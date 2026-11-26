import httpx
import numpy as np
import time


class APIEmbedding:
    def __init__(self, settings):
        self.settings = settings
        self.model_id = f'api:{settings.embedding_base_url}:{settings.embedding_model}'
        if not settings.embedding_api_key.get_secret_value():
            raise RuntimeError('Set RA_EMBEDDING_API_KEY or select local embeddings')

    def embed(self, texts):
        vectors = []
        deadline = time.monotonic() + self.settings.timeout_seconds
        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            for start in range(0, len(texts), 32):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise httpx.TimeoutException('Embedding batch deadline exceeded')
                batch = texts[start:start+32]
                response = client.post(self.settings.embedding_base_url.rstrip('/')+'/embeddings',
                    headers={'Authorization': 'Bearer '+self.settings.embedding_api_key.get_secret_value()},
                    json={'model': self.settings.embedding_model, 'input': batch}, timeout=remaining)
                response.raise_for_status()
                try:
                    rows = sorted(response.json()['data'], key=lambda x: x['index'])
                    if [r['index'] for r in rows] != list(range(len(batch))):
                        raise ValueError('Incorrect embedding indices')
                    vectors.extend(r['embedding'] for r in rows)
                except (ValueError, KeyError, TypeError) as exc:
                    raise httpx.DecodingError('Invalid embedding response') from exc
        return np.array(vectors, dtype=np.float32)


class LocalEmbedding:
    def __init__(self, model_name):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.model_id = 'local:'+model_name

    def embed(self, texts):
        return self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)


def make_embedding(settings):
    if settings.embedding_backend == 'local':
        return LocalEmbedding(settings.embedding_model)
    if settings.embedding_backend != 'api':
        raise ValueError('RA_EMBEDDING_BACKEND must be api or local')
    return APIEmbedding(settings)
