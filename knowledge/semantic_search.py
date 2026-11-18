"""Semantic search engine leveraging ChromaDB dense embeddings for English, Hindi, and Hinglish queries."""

from dataclasses import dataclass, field
import re
from typing import Any, Optional
from knowledge.ingestion import SchemeIngestionPipeline
from knowledge.vector_store import VectorStoreManager

HINGLISH_INTENT_MAP = {
    "padhai": "education student scholarship college",
    "shiksha": "education student scholarship school",
    "chhatravritti": "scholarship financial support student grant",
    "kheti": "farmer agriculture farming crop kisan",
    "kisan": "farmer agriculture farming rural",
    "fasal": "crop agriculture harvest seeds",
    "ilaj": "health medical hospital treatment insurance",
    "dawa": "medicine health medical treatment hospital",
    "bimari": "illness health medical hospital care",
    "swasthya": "health medical hospital insurance ayushman",
    "karz": "loan credit financial assistance business",
    "vyapar": "business micro enterprise self employment mudra",
    "dukan": "shop business micro enterprise self employed",
    "ghar": "housing home house shelter awas",
    "makaan": "housing home house shelter awas",
    "awas": "housing home house shelter gramin",
    "vriddha": "senior citizen old age pension retired",
    "budhapa": "senior citizen old age pension elderly",
    "mahila": "women woman girl female shg didi",
    "beti": "girl daughter woman female child sukanya",
    "divyang": "disability disabled handicapped assistive aid",
    "viklang": "disability disabled handicapped assistive aid",
    "machhli": "fisheries aquaculture fishing matsya sampada",
    "matsya": "fisheries aquaculture fishing matsya sampada",
}


def expand_query_intent(query: str) -> str:
    """Expands Hinglish and Hindi terms with semantic intent concepts to enhance dense retrieval."""
    words = re.findall(r"\b\w+\b", query.lower())
    expansions = []
    for w in words:
        if w in HINGLISH_INTENT_MAP:
            expansions.append(HINGLISH_INTENT_MAP[w])

    if expansions:
        unique_concepts = " ".join(set(" ".join(expansions).split()))
        return f"{query} {unique_concepts}"
    return query


@dataclass
class SemanticSearchResult:
    """Structured result returned by ChromaDB semantic query."""
    scheme_id: str
    name: str
    score: float
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)
    official_url: str = ""
    ministry: str = ""


class SemanticSearchEngine:
    """Queries persistent ChromaDB collection using dense multilingual vector similarity."""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store or VectorStoreManager()
        self.ingestion = SchemeIngestionPipeline(self.vector_store)

    def ensure_indexed(self, force_refresh: bool = False):
        """Ensures the vector store is populated with schemes."""
        if force_refresh or self.vector_store.count() == 0:
            self.ingestion.ingest_all(force_reset=force_refresh)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_active: bool = True,
        where_filter: Optional[dict[str, Any]] = None,
    ) -> list[SemanticSearchResult]:
        """Performs semantic similarity search over scheme documents.

        Supports English, Hindi, and Hinglish intent even when wording differs from scheme titles.
        Returns source metadata and confidence scores with every result.
        """
        self.ensure_indexed()
        collection = self.vector_store.get_collection()

        where: Optional[dict[str, Any]] = None
        if filter_active and where_filter:
            where = {"$and": [{"is_active": True}, where_filter]}
        elif filter_active:
            where = {"is_active": True}
        elif where_filter:
            where = where_filter

        enriched_query = expand_query_intent(query.strip()) or "government schemes and benefits"
        query_texts = [enriched_query]

        results = collection.query(
            query_texts=query_texts,
            n_results=min(top_k, max(1, self.vector_store.count())),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results: list[SemanticSearchResult] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [1.0] * len(ids)

        for sid, doc, meta, dist in zip(ids, docs, metas, distances):
            similarity_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            meta_dict = meta if isinstance(meta, dict) else {}

            search_results.append(
                SemanticSearchResult(
                    scheme_id=sid,
                    name=meta_dict.get("name", sid),
                    score=round(similarity_score, 4),
                    document=doc,
                    metadata=meta_dict,
                    official_url=meta_dict.get("official_url", ""),
                    ministry=meta_dict.get("ministry", ""),
                )
            )

        return search_results

    def get_scheme_evidence(self, scheme_id: str) -> Optional[dict[str, Any]]:
        """Retrieves raw indexed document and source metadata for a specific scheme."""
        self.ensure_indexed()
        collection = self.vector_store.get_collection()
        record = collection.get(ids=[scheme_id], include=["documents", "metadatas"])
        if record and record.get("ids") and record["ids"]:
            doc = record["documents"][0] if record.get("documents") else ""
            meta = record["metadatas"][0] if record.get("metadatas") else {}
            return {
                "scheme_id": scheme_id,
                "document": doc,
                "metadata": meta,
                "official_url": meta.get("official_url", "") if isinstance(meta, dict) else "",
            }
        return None
