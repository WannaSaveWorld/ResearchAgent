import asyncio
import logging
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from researchagent.config import Settings
from researchagent.store import Store

logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    external: bool = False

    @field_validator('question')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Question must not be blank')
        return value.strip()


def create_app(settings=None, workflow_factory=None):
    settings = settings or Settings()
    store = Store(settings)
    app = FastAPI(title='ResearchAgent', version='0.1.0')
    app.state.store = store
    app.state.embedding = None

    def retriever(mode='hybrid'):
        from researchagent.embeddings import make_embedding
        from researchagent.retrieval import HybridRetriever
        if mode == 'bm25':
            return HybridRetriever(store.chunks(), None, store.root/'index')
        if app.state.embedding is None:
            app.state.embedding = make_embedding(settings)
        return HybridRetriever(store.chunks(), app.state.embedding, store.root/'index')

    def workflow():
        if workflow_factory:
            return workflow_factory()
        from researchagent.paperqa_engine import PaperQAEngine
        from researchagent.tools import MCPPaperSearch
        from researchagent.workflow import ResearchWorkflow
        engine = PaperQAEngine(settings)
        return ResearchWorkflow(retriever(), engine,
            tool=MCPPaperSearch(settings.mcp_url, settings.mcp_tool, settings.timeout_seconds),
            timeout=settings.timeout_seconds, top_k=settings.top_k,
            max_tool_calls=settings.max_tool_calls, recursion_limit=settings.graph_recursion_limit)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse(status_code=404, content={'detail': 'Document or session not found'})

    @app.get('/', response_class=HTMLResponse)
    def home():
        return (Path(__file__).parent/'static'/'index.html').read_text('utf-8')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'documents': len(store.documents()),
                'chat_configured': bool(settings.chat_api_key.get_secret_value()),
                'embedding_backend': settings.embedding_backend}

    @app.post('/documents')
    async def upload(file: UploadFile = File(...)):
        data = await file.read(settings.max_upload_bytes+1)
        await file.close()
        try:
            return await asyncio.to_thread(store.add_pdf, data, file.filename or 'paper.pdf')
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get('/documents')
    def documents():
        return store.documents()

    @app.get('/documents/{doc_id}/source')
    def source(doc_id: str, page: int = Query(default=1, ge=1)):
        doc = store.get_document(doc_id)
        if page > doc.pages:
            raise HTTPException(422, 'Page is outside the document')
        return FileResponse(store.document_path(doc_id), media_type='application/pdf',
                            filename=doc.filename, content_disposition_type='inline',
                            headers={'X-Source-Page': str(page), 'X-Content-Type-Options': 'nosniff'})

    @app.post('/sessions')
    def create_session():
        return {'id': store.create_session()}

    @app.get('/sessions/{session_id}')
    def session(session_id: str):
        return {'id': session_id, 'messages': store.messages(session_id)}

    @app.get('/search')
    async def search(q: str = Query(min_length=1, max_length=4000),
                     mode: Literal['bm25', 'vector', 'hybrid'] = 'hybrid',
                     k: int = Query(default=6, ge=1, le=20)):
        try:
            r = await asyncio.to_thread(retriever, mode)
            return await asyncio.to_thread(r.search, q, k, mode)
        except RuntimeError:
            raise HTTPException(503, 'Embedding configuration missing or unavailable') from None
        except ValueError:
            raise HTTPException(409, 'Index or embedding mismatch; check configuration and rebuild') from None
        except httpx.HTTPError:
            raise HTTPException(502, 'Embedding service request failed') from None

    @app.post('/ask')
    async def ask(body: AskRequest):
        session_id = body.session_id or store.create_session()
        history = store.messages(session_id)
        # Persisted user questions supply limited topic context; answers are not
        # reused as evidence and cannot create citations for the new answer.
        previous = [m['content'] for m in history if m['role'] == 'user'][-3:]
        question = body.question
        if previous:
            question = 'Previous user questions (topic context only):\n' + '\n'.join(previous) + \
                       '\nCurrent question: '+question
        try:
            async with asyncio.timeout(settings.timeout_seconds):
                w = await asyncio.to_thread(workflow)
                answer = await w.ask(question, external=body.external)
        except TimeoutError:
            raise HTTPException(504, 'Research request timed out') from None
        except RuntimeError:
            raise HTTPException(503, 'Model or tool configuration unavailable; check .env') from None
        except httpx.HTTPError:
            raise HTTPException(502, 'Upstream model service request failed') from None
        except ValueError:
            raise HTTPException(409, 'Index or model response invalid; check configuration') from None
        except Exception:
            logger.warning('Research request failed; details omitted to avoid exposing credentials')
            raise HTTPException(502, 'Research pipeline failed; check provider and model compatibility') from None
        store.add_message(session_id, 'user', body.question)
        store.add_message(session_id, 'assistant', answer.model_dump_json())
        return {'session_id': session_id, **answer.model_dump()}

    return app


def app_factory():
    return create_app()
