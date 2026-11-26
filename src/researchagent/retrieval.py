import hashlib
import json
import re
from pathlib import Path
import faiss
import jieba
import numpy as np
from filelock import FileLock
from rank_bm25 import BM25Okapi
from researchagent.models import Hit

jieba.setLogLevel(40)


def tokens(text):
    result = []
    for part in re.findall(r'[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*|[\u4e00-\u9fff]+', text.lower()):
        result.extend(jieba.lcut(part) if re.search(r'[\u4e00-\u9fff]', part) else [part])
    return result


def rrf(rankings, constant=60):
    scores = {}
    for ranking in rankings:
        seen = set()
        for rank, key in enumerate(ranking, 1):
            if key not in seen:
                scores[key] = scores.get(key, 0) + 1/(constant+rank)
                seen.add(key)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


class HybridRetriever:
    def __init__(self, chunks, embedding, index_dir):
        self.chunks = chunks
        self.embedding = embedding
        self.by_id = {c.id: c for c in chunks}
        self.terms = [tokens(c.text) or ['_empty_'] for c in chunks]
        self.bm25 = BM25Okapi(self.terms) if chunks else None
        self.index = None
        if not chunks or embedding is None:
            return
        root = Path(index_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        fingerprint = hashlib.sha256(''.join(c.model_dump_json() for c in chunks).encode()).hexdigest()
        with FileLock(str(root/'index.lock'), timeout=120):
            manifest_path, index_path = root/'manifest.json', root/'index.faiss'
            manifest = json.loads(manifest_path.read_text('utf-8')) if manifest_path.exists() else None
            if manifest and manifest['model'] != embedding.model_id:
                raise ValueError('Embedding model changed; rebuild index in a new data/index directory')
            if manifest and manifest['corpus'] == fingerprint and index_path.exists():
                blob = index_path.read_bytes()
                if hashlib.sha256(blob).hexdigest() != manifest['index_sha256']:
                    raise ValueError('Index damaged; rebuild index')
                self.index = faiss.deserialize_index(np.frombuffer(blob, dtype=np.uint8).copy())
                if self.index.ntotal != len(chunks) or self.index.d != manifest['dimension']:
                    raise ValueError('Index shape mismatch; rebuild index')
            else:
                vectors = self._vectors([c.text for c in chunks])
                self.index = faiss.IndexFlatIP(vectors.shape[1])
                self.index.add(vectors)
                blob = faiss.serialize_index(self.index).tobytes()
                temporary = root/'index.tmp'
                temporary.write_bytes(blob)
                temporary.replace(index_path)
                metadata = dict(model=embedding.model_id, corpus=fingerprint, dimension=self.index.d,
                                index_sha256=hashlib.sha256(blob).hexdigest())
                tmp_manifest = root/'manifest.tmp'
                tmp_manifest.write_text(json.dumps(metadata), encoding='utf-8')
                tmp_manifest.replace(manifest_path)

    def _vectors(self, texts):
        values = np.asarray(self.embedding.embed(texts), dtype=np.float32)
        if values.ndim != 2 or values.shape[0] != len(texts) or values.shape[1] == 0:
            raise ValueError('Invalid embedding shape')
        if not np.isfinite(values).all() or np.any(np.linalg.norm(values, axis=1) == 0):
            raise ValueError('Invalid embedding values')
        values = np.ascontiguousarray(values)
        faiss.normalize_L2(values)
        return values

    def search(self, question, k=6, mode='hybrid'):
        if not 1 <= k <= 100 or mode not in {'bm25', 'vector', 'hybrid'}:
            raise ValueError('Invalid search k or mode')
        if not self.chunks:
            return []
        query_terms = tokens(question)
        if not query_terms:
            return []
        scores = self.bm25.get_scores(query_terms)
        lexical = [i for i in np.argsort(-scores, kind='stable')
                   if set(query_terms) & set(self.terms[i])][:max(20, k*3)]
        bm_ids = [self.chunks[i].id for i in lexical]
        if mode == 'bm25':
            return [Hit(chunk=self.chunks[i], score=float(scores[i])) for i in lexical[:k]]
        if self.index is None:
            raise RuntimeError('Vector search requires an embedding provider')
        query = self._vectors([question])
        if query.shape[1] != self.index.d:
            raise ValueError('Query embedding dimension changed; rebuild index')
        similarities, indices = self.index.search(query, min(len(self.chunks), max(20, k*3)))
        vector = [(self.chunks[int(i)].id, float(s)) for i, s in zip(indices[0], similarities[0])
                  if i >= 0 and s > 0]
        if mode == 'vector':
            return [Hit(chunk=self.by_id[key], score=s) for key, s in vector[:k]]
        return [Hit(chunk=self.by_id[key], score=s)
                for key, s in rrf([bm_ids, [key for key, _ in vector]])[:k]]
