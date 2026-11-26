import numpy as np
import pytest
from researchagent.models import Chunk
from researchagent.retrieval import HybridRetriever, rrf


class FakeEmbedding:
    """Deterministic test double; never a production embedding provider."""
    model_id = 'test-semantic-v1'

    def embed(self, texts):
        return np.array([[1.0, 0.0] if ('thermal' in t or '红外' in t)
                         else [0.0, 1.0] for t in texts], dtype=np.float32)


def chunks():
    return [Chunk(id='a', document_id='d', filename='a.pdf', page=1, section='Intro',
                  text='thermal 红外 fusion temperature'),
            Chunk(id='b', document_id='d', filename='a.pdf', page=2, section='Methods',
                  text='database cache redis transactions'),
            Chunk(id='c', document_id='e', filename='b.pdf', page=1, section='Results',
                  text='thermal saliency 深度融合')]


def test_rrf_deduplicates_and_combines():
    assert rrf([['a', 'b'], ['b', 'c']])[0][0] == 'b'
    assert len(rrf([['a', 'a'], []])) == 1


def test_real_faiss_index_restart_and_model_mismatch(tmp_path):
    r = HybridRetriever(chunks(), FakeEmbedding(), tmp_path)
    assert r.search('thermal', k=2)[0].chunk.id in {'a', 'c'}
    assert r.search('redis database', mode='bm25')[0].chunk.id == 'b'
    assert (tmp_path/'index.faiss').exists()
    again = HybridRetriever(chunks(), FakeEmbedding(), tmp_path)
    assert again.search('thermal', mode='vector')[0].chunk.page in {1}
    wrong = FakeEmbedding()
    wrong.model_id = 'other-model'
    with pytest.raises(ValueError, match='rebuild'):
        HybridRetriever(chunks(), wrong, tmp_path)


def test_empty_and_no_keyword_evidence(tmp_path):
    r = HybridRetriever([], FakeEmbedding(), tmp_path)
    assert r.search('anything') == []
    r = HybridRetriever(chunks(), FakeEmbedding(), tmp_path/'other')
    assert r.search('unmatchedwords', mode='bm25') == []
    with pytest.raises(ValueError):
        r.search('thermal', k=0)
