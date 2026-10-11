from app.memory.manager import memory_manager
from app.embeddings import embedding_engine


class RAGEngine:

    def retrieve(self, query, limit=5):

        memories = memory_manager.all()

        if not memories:
            return []

        return embedding_engine.semantic_search(
            query,
            memories,
            limit
        )

    def build_context(self, query):

        documents = self.retrieve(query)

        if not documents:
            return "No relevant memories found."

        return "\n".join(
            f"- {doc['content']}"
            for doc in documents
        )


rag = RAGEngine()