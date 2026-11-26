# ResearchAgent · Scientific Literature Assistant

**English** | [简体中文](README.zh-CN.md)

An independent literature assistant built on [PaperQA](https://github.com/Future-House/paper-qa), extended with PDF page provenance, BM25 + FAISS + RRF hybrid retrieval, LangGraph orchestration, FastAPI, and opt-in external paper search through MCP.

Designed for literature reviews, research discussions, and checking claims against source documents. Answers include evidence passages and sources; users should still verify that the evidence supports each claim.

## Features

- **Document ingestion:** content-hash deduplication, page-level text extraction, common section-heading recognition, chunking, and PDF page indices and labels.
- **Hybrid retrieval:** BM25 lexical retrieval and FAISS cosine-similarity search over real embeddings, combined with reciprocal rank fusion (RRF).
- **PaperQA integration:** hybrid retrieval selects candidates; PaperQA summarizes evidence and generates cited answers, with its additional retrieval disabled.
- **Source validation:** citations must map to actual candidates. Pages come from parser metadata; unknown citations or answers without valid citations are rejected.
- **Agent workflow:** LangGraph coordinates local retrieval, optional external search, answer generation, and citation checks, with step and timeout limits.
- **Local service:** a Chinese-language upload and question-answering interface, interactive API documentation, and SQLite persistence for documents and sessions.
- **Evaluation:** synthetic documents, labelled questions, Recall@k/MRR@k evaluation, and protocol tests without real credentials.

## Quick Start

Python 3.12 is recommended; supported versions are Python 3.11–3.13. Run commands from the repository root.

### Windows / PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

On Windows, if installation fails because of long dependency paths, use a shorter checkout path such as `D:\ResearchAgent` and retry. No registry changes are required. Keep `.venv` out of Git.

Configure the chat and embedding services in `.env`, then start:

```bash
python -m uvicorn researchagent.api:app_factory --factory --host 127.0.0.1 --port 8000
```

- Web interface: <http://127.0.0.1:8000>
- API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

The default setup is for local, single-user use. Authentication, tenant isolation, and production operations are not included.

## Model Configuration

Supply your own credentials for compatible chat and embeddings APIs. `RA_CHAT_MODEL` uses a LiteLLM identifier. Replace models and endpoints with those supported by your provider. Never commit real keys.

```dotenv
RA_CHAT_MODEL=openai/gpt-4o-mini
RA_CHAT_BASE_URL=https://api.openai.com/v1
RA_CHAT_API_KEY=your-key
RA_EMBEDDING_BACKEND=api
RA_EMBEDDING_MODEL=text-embedding-3-small
RA_EMBEDDING_BASE_URL=https://api.openai.com/v1
RA_EMBEDDING_API_KEY=your-key
```

These are examples, not included API credits or a guarantee of compatibility with every provider. Confirm that your documents may be sent to the chosen remote services before sending passages for embedding or answer generation.

For local embeddings, install `python -m pip install -e ".[local]"`, set `RA_EMBEDDING_BACKEND=local`, and set `RA_EMBEDDING_MODEL` to a sentence-transformers model name or local path. Initial downloads need network access and disk space. Chat inference is configured separately. Production semantic retrieval never substitutes random or hash-based vectors for actual embeddings.

**Without API keys**, you can still upload documents, inspect sources, use `/search?mode=bm25&q=...`, run offline tests, and evaluate the BM25 demo. Chat and semantic retrieval return explicit configuration errors when required settings are missing.

## External Paper Search (Optional)

Start the example MCP server, which queries the arXiv metadata API:

```bash
python examples/mcp_paper_search.py
```

Configure `.env`, restart ResearchAgent, and enable external paper search in the interface:

```dotenv
RA_MCP_URL=http://127.0.0.1:8001/mcp
RA_MCP_TOOL=search_papers
```

**The tool runs only when local retrieval returns no candidates and the user explicitly opts in**, at most once per request. When disabled, the external service is not contacted. The initial implementation does not let the model execute arbitrary tools.

Tool input: `{"query":"..."}`. Output: `{"results":[{"title":"...","url":"https://...","text":"abstract or evidence"}]}`. External evidence uses source URLs, not invented PDF pages. The example searches abstracts rather than downloading full papers and is subject to arXiv availability and usage requirements.

## Demo and Evaluation

```bash
python scripts/demo.py
python scripts/evaluate.py --modes bm25 --k 3
# After configuring real embeddings, compare all three modes:
python scripts/evaluate.py --modes bm25 vector hybrid --k 3
```

The demo contains **five original synthetic documents, ten pages, and ten questions**. These are not published papers or a real-world laboratory benchmark. Results are saved to `data/evaluation.json`. Recall@k and MRR@k are document-level metrics after deduplicating documents, not chunk-level metrics. Supply a labelled JSON file with `--questions`:

```json
[{"question":"Research question","relevant_files":["paper.pdf"]}]
```

Use unique filenames in evaluation labels. A meaningful benchmark should include more questions, paraphrases, hard negatives, and unanswerable queries. High synthetic-demo scores do not establish real-world retrieval improvements.

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service and configuration status; never returns keys |
| POST / GET | `/documents` | Upload / list PDFs |
| GET | `/documents/{id}/source?page=1` | Return the original PDF; viewers can append `#page=1` |
| GET | `/search?q=...&mode=hybrid&k=6` | Retrieve candidates and scores |
| POST | `/sessions` | Create a session |
| GET | `/sessions/{id}` | Read saved messages |
| POST | `/ask` | Submit a question, optional `session_id`, and `external` flag |

Sessions persist messages and use the latest three user questions as limited topic context. This is not a full conversational query-rewriting system. Previous answers are not reused as documentary evidence. Successful requests save the user question and structured answer.

## Testing

```bash
python -m pytest -q
python -m ruff check src tests scripts examples
python -m pip check
```

Tests exercise real FAISS, the PaperQA evidence and answer pipeline, LangGraph, the API, and local HTTP protocols. LLMs and some embeddings are **explicit test doubles**; these tests do not measure provider quality or model accuracy. Real credentials, hosted models, and live arXiv access require separate validation.

`requirements-lock.txt` records the reference environment (Python 3.12 / Windows). For other platforms, prefer installation through `pyproject.toml`; the reference lock includes platform markers where applicable.

## Data and Indexes

By default, `data/` contains SQLite storage, original PDFs, the FAISS index, and its manifest. These are excluded from Git. Do not load untrusted indexes. Filenames are display metadata; PDFs are stored under SHA-256 identifiers.

The manifest records the embedding model, corpus fingerprint, vector dimension, and index checksum. Adding documents triggers a rebuild. When changing the embedding model, use a new data directory or stop the service, back up the index directory, and rebuild it. The initial implementation targets small collections and does not provide incremental vector updates or distributed indexing.

## Upstream and Project Contributions

**PaperQA provides:** document and chunk models, evidence summarization, cited answer generation, and formatting.

**This project adds:** page-level parsing and provenance, SQLite storage, BM25/FAISS/RRF retrieval, candidate-injection adaptation, citation validation, LangGraph orchestration, bounded MCP calls, a FastAPI interface, evaluation, and tests.

PaperQA is integrated as a dependency; its full repository has not been copied and renamed. Attribution and the Apache-2.0 license are retained. Third-party components remain subject to their own licenses. See [architecture and limitations](docs/architecture.md) and [validation notes](docs/validation.md), currently available in Chinese.
