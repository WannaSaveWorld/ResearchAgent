"""Local protocol tests, not claims of live provider or laboratory deployment."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
import httpx
from pydantic import SecretStr
from researchagent.config import Settings
from researchagent.embeddings import APIEmbedding
from researchagent.models import Chunk, Hit
from researchagent.paperqa_engine import PaperQAEngine


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path.endswith('/embeddings'):
            out = {'data': [{'index': i, 'embedding': [1.0, 0.5, 0.0]}
                            for i, _ in enumerate(body['input'])]}
        else:
            from paperqa.utils import get_citation_ids
            prompt = '\n'.join(str(m.get('content', '')) for m in body['messages'])
            if 'Valid Keys:' in prompt:
                keys = sorted(get_citation_ids(prompt) - {'pqac-0f650d59'})
                text = f'Thermal data complements RGB ({keys[0]}).'
            else:
                text = json.dumps({'summary': 'Thermal data provides complementary evidence in dark scenes '
                                   'and the paper evaluates this information for salient object detection.',
                                   'relevance_score': 9})
            out = {'id': 'chatcmpl-local-test', 'object': 'chat.completion', 'created': 0,
                   'model': body['model'], 'choices': [{'index': 0,
                   'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def endpoint():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/v1'
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_real_embedding_http_protocol(endpoint, tmp_path):
    settings = Settings(data_dir=tmp_path, embedding_base_url=endpoint,
                        embedding_api_key=SecretStr('local-test-key'))
    assert APIEmbedding(settings).embed(['one', 'two']).shape == (2, 3)


def test_bad_embedding_payload_is_upstream_error(monkeypatch, tmp_path):
    def bad(*args, **kwargs):
        return httpx.Response(200, json={'data': [{'index': 0}]},
                              request=httpx.Request('POST', 'https://example.org/embeddings'))
    monkeypatch.setattr(httpx.Client, 'post', bad)
    provider = APIEmbedding(Settings(data_dir=tmp_path, embedding_api_key=SecretStr('test')))
    with pytest.raises(httpx.DecodingError):
        provider.embed(['example'])


async def test_real_paperqa_litellm_http_protocol(endpoint, tmp_path):
    settings = Settings(data_dir=tmp_path, chat_base_url=endpoint,
                        chat_api_key=SecretStr('local-test-key'))
    c = Chunk(id='local', document_id='d', filename='s.pdf', page=2,
              text='Thermal data provides complementary evidence for detecting objects in dark scenes.')
    out = await PaperQAEngine(settings).answer('How does thermal help?', [Hit(chunk=c, score=1)])
    assert not out.refused
    assert out.citations[0].page == 2
