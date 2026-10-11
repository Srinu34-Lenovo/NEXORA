import numpy as np
from threading import Lock, Thread

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class EmbeddingEngine:

    def __init__(self):

        self.model = None
        self._model_load_lock = Lock()
        self._model_load_started = False

    def _load_model(self):

        try:
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.model = None

    def _start_model_load(self):

        if SentenceTransformer is None or self._model_load_started:
            return

        with self._model_load_lock:
            if self._model_load_started:
                return

            self._model_load_started = True
            Thread(target=self._load_model, daemon=True).start()

    def encode(self, text):

        model = self.model
        if model is None:
            self._start_model_load()
            return None

        return model.encode(
            text,
            normalize_embeddings=True
        )

    def similarity(self, a, b):

        if a is None or b is None:
            return 0.0

        return float(np.dot(a, b))

    def semantic_search(self, query, documents, limit=5):

        model = self.model
        if model is None:
            self._start_model_load()
            return documents[:limit]

        vectors = model.encode(
            [query] + [document["content"] for document in documents],
            normalize_embeddings=True
        )
        query_vector = vectors[0]
        results = [
            (self.similarity(query_vector, vector), document)
            for document, vector in zip(documents, vectors[1:])
        ]

        results.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return [
            document
            for score, document in results[:limit]
        ]


embedding_engine = EmbeddingEngine()