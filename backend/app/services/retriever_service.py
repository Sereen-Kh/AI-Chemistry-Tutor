import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings


class RetrieverService:
    client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    embedding_function = (embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2"))
    collection = client.get_or_create_collection(
        name="chemistry_material",
        embedding_function=embedding_function,
    )


    @staticmethod
    def retrieve_lesson_content(lesson: str,) -> str:
        result = RetrieverService.collection.get(where={"lesson": lesson})
        if not result["documents"]:
            raise ValueError(f"No content found for lesson: {lesson}")

        return "\n".join(result["documents"])