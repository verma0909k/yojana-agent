"""Ingestion pipeline to index government schemes into ChromaDB with rich metadata and multilingual keywords."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional
from knowledge.schemes.data import load_all_schemes
from knowledge.vector_store import VectorStoreManager
from shared.config import SCHEMES_DIR
from shared.schemas import Scheme

CATEGORY_EXPANSIONS = {
    "student": "student scholarship education college school padhai shiksha chhatravritti",
    "scholarship": "scholarship financial aid tuition fee stipend chhatravritti",
    "farmer": "farmer agriculture farming crop kisan kheti krishi fasal",
    "agriculture": "agriculture farming crops seeds irrigation kisan",
    "health": "health medical insurance hospital treatment ilaj swasthya bimari ayushman",
    "healthcare": "healthcare medical treatment hospital ilaj dawa",
    "business": "business micro enterprise self employment loan credit vyapar karz mudra",
    "loan": "loan credit financial assistance subsidy rin karz",
    "women": "women female girl daughter mahila beti nari shg",
    "housing": "housing home house shelter awas ghar makaan",
    "pension": "pension elderly senior citizen retirement vriddha budhapa",
    "disability": "disability disabled handicapped divyang viklang assistive",
    "fisheries": "fisheries aquaculture fishing matsya machhli palan",
}


def build_scheme_search_document(scheme: Scheme) -> str:
    """Constructs a rich text representation of a scheme for dense semantic retrieval."""
    lines = [
        f"Scheme: {scheme.name}",
    ]
    if scheme.name_hi:
        lines.append(f"Hindi Name: {scheme.name_hi}")

    lines.extend([
        f"Ministry: {scheme.ministry}",
        f"Description: {scheme.description}",
        f"Benefits: {scheme.benefits}",
        f"Official Portal: {scheme.official_url}",
    ])

    if scheme.category_tags:
        lines.append(f"Tags & Target Beneficiaries: {', '.join(scheme.category_tags)}")
        # Add multilingual concept expansions
        expansions = []
        for tag in scheme.category_tags:
            tag_clean = tag.lower().strip()
            if tag_clean in CATEGORY_EXPANSIONS:
                expansions.append(CATEGORY_EXPANSIONS[tag_clean])
        if expansions:
            lines.append(f"Multilingual Keywords: {' '.join(set(' '.join(expansions).split()))}")

    if scheme.documents_required:
        lines.append(f"Documents Required: {', '.join(scheme.documents_required)}")

    if scheme.criteria:
        criteria_descriptions = [c.description for c in scheme.criteria if c.description]
        if criteria_descriptions:
            lines.append(f"Eligibility Conditions: {'; '.join(criteria_descriptions)}")

    return "\n".join(lines)


def build_scheme_metadata(scheme: Scheme) -> dict[str, Any]:
    """Extracts searchable metadata attributes suitable for ChromaDB scalar filtering."""
    return {
        "scheme_id": scheme.id,
        "name": scheme.name,
        "name_hi": scheme.name_hi or "",
        "ministry": scheme.ministry,
        "official_url": scheme.official_url,
        "is_active": scheme.is_active,
        "category_tags": ", ".join(scheme.category_tags),
        "benefits_summary": scheme.benefits[:200],
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


class SchemeIngestionPipeline:
    """Handles parsing, document formation, and idempotent upsert into ChromaDB."""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store or VectorStoreManager()

    def ingest_all(self, schemes_dir: Optional[Path] = None, force_reset: bool = False) -> dict[str, Any]:
        """Ingests all scheme JSON files into ChromaDB without duplication."""
        schemes = load_all_schemes(schemes_dir or SCHEMES_DIR)
        collection = self.vector_store.reset_collection() if force_reset else self.vector_store.get_collection()

        ids = []
        documents = []
        metadatas = []

        for s in schemes:
            ids.append(s.id)
            documents.append(build_scheme_search_document(s))
            metadatas.append(build_scheme_metadata(s))

        if ids:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

        return {
            "total_schemes": len(schemes),
            "ingested_count": len(ids),
            "collection_count": collection.count(),
        }
