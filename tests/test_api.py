from fastapi.testclient import TestClient
from researchagent.api import create_app
from researchagent.config import Settings
from researchagent.models import Answer
from test_ingest import pdf_bytes


class Workflow:
    async def ask(self, question, external=False):
        return Answer(answer='test answer', refused=False)


def test_api_upload_sessions_and_source(tmp_path):
    app = create_app(Settings(data_dir=tmp_path), workflow_factory=lambda: Workflow())
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/health').json()['status'] == 'ok'
        out = client.post('/documents', files={'file': ('../../a.pdf', pdf_bytes('Example paper.'),
                                                       'application/pdf')})
        assert out.status_code == 200, out.text
        doc = out.json()
        assert doc['filename'] == 'a.pdf'
        assert client.get(f"/documents/{doc['id']}/source?page=1").status_code == 200
        assert client.get(f"/documents/{doc['id']}/source?page=99").status_code == 422
        a = client.post('/sessions').json()['id']
        b = client.post('/sessions').json()['id']
        response = client.post('/ask', json={'question': 'What?', 'session_id': a})
        assert response.status_code == 200, response.text
        assert len(client.get('/sessions/'+a).json()['messages']) == 2
        assert client.get('/sessions/'+b).json()['messages'] == []
        assert client.post('/ask', json={'question': ' ', 'session_id': a}).status_code == 422
        assert client.get('/sessions/no').status_code == 404
        assert client.post('/documents', files={'file': ('bad.pdf', b'no')}).status_code == 422


def test_missing_model_configuration_is_explicit(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        out = client.post('/ask', json={'question': 'What is fusion?'})
        assert out.status_code == 503
        assert 'traceback' not in out.text.lower()
