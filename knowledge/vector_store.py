"""Persistent ChromaDB vector store initialization and collection management."""

from pathlib import Path
from typing import Any, Optional
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from shared.config import CHROMA_COLLECTION_NAME, CHROMA_DIR, EMBEDDING_PROVIDER, GOOGLE_API_KEY


def get_embedding_function(provider: Optional[str] = None) -> Any:
    """Returns the configured embedding function.

    Supports:
    - 'default' / 'onnx': Local ONNX MiniLM model (384 dims, fast, offline).
    - 'gemini': Google Generative AI embeddings if GOOGLE_API_KEY is available.
    """
    prov = (provider or EMBEDDING_PROVIDER).lower()
    
    if prov in ("gemini", "google") and GOOGLE_API_KEY:
        try:
            return embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=GOOGLE_API_KEY,
                model_name="models/embedding-001"
            )
        except Exception:
            pass  # Fall back to default local ONNX model

    # Default to local ONNX MiniLM embedding function
    return embedding_functions.DefaultEmbeddingFunction()


class VectorStoreManager:
    """Manages persistent ChromaDB vector store for government scheme semantic indexing."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME
        self.embedding_function = embedding_function or get_embedding_function()

        # Initialize persistent Chroma client
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection: Optional[Collection] = None

    def get_collection(self) -> Collection:
        """Retrieves or creates the schemes collection with configured embedding function."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def reset_collection(self) -> Collection:
        """Deletes and recreates the collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None
        return self.get_collection()

    def count(self) -> int:
        """Returns the number of indexed documents in the collection."""
        return self.get_collection().count()
