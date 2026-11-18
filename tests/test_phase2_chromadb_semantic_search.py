"""Unit tests for Phase 2: ChromaDB Integration, Scheme Ingestion, and Multilingual Semantic Search."""

from knowledge.ingestion import SchemeIngestionPipeline
from knowledge.semantic_search import SemanticSearchEngine
from knowledge.vector_store import VectorStoreManager


def test_chromadb_ingestion_and_deduplication(tmp_path):
    """Verify that all scheme JSON files are ingested into ChromaDB without duplication on repeated runs."""
    manager = VectorStoreManager(persist_dir=tmp_path / "chroma_test", collection_name="test_schemes")
    pipeline = SchemeIngestionPipeline(vector_store=manager)

    # 1. First ingestion
    report1 = pipeline.ingest_all()
    count1 = report1["collection_count"]
    assert count1 >= 21

    # 2. Second ingestion should upsert without duplicating IDs
    report2 = pipeline.ingest_all()
    count2 = report2["collection_count"]
    assert count2 == count1


def test_semantic_search_hinglish_queries(tmp_path):
    """Verify semantic retrieval for Hinglish queries without requiring exact keyword matches."""
    manager = VectorStoreManager(persist_dir=tmp_path / "chroma_test_search", collection_name="test_search")
    engine = SemanticSearchEngine(vector_store=manager)
    engine.ensure_indexed(force_refresh=True)

    # Query 1: Hinglish education query -> should retrieve scholarship schemes
    edu_query = "Mujhe padhai ke liye paise ki help chahiye. Family income kam hai."
    edu_results = engine.search(edu_query, top_k=3)
    assert len(edu_results) >= 1
    top_edu_ids = [r.scheme_id for r in edu_results]
    assert any(sid in top_edu_ids for sid in ["post-matric-scholarship", "aicte-pragati-scholarship", "nsp-national-scholarship-portal"])

    # Every result must preserve official URL and metadata
    for r in edu_results:
        assert r.official_url != ""
        assert "scheme_id" in r.metadata
        assert 0.0 <= r.score <= 1.0

    # Query 2: Agriculture / solar pump query -> should retrieve PM-KUSUM or PM-KISAN
    farm_query = "khet me kisan ko solar water pump aur sinchai ke liye sahayata"
    farm_results = engine.search(farm_query, top_k=3)
    top_farm_ids = [r.scheme_id for r in farm_results]
    assert any(sid in top_farm_ids for sid in ["pm-kusum", "pm-kisan"])

    # Query 3: Health insurance query -> should retrieve PM-JAY
    health_query = "hospital me ilaj ke liye bima aur free treatment"
    health_results = engine.search(health_query, top_k=3)
    top_health_ids = [r.scheme_id for r in health_results]
    assert "pm-jay" in top_health_ids


def test_semantic_search_metadata_filtering(tmp_path):
    """Verify that metadata filters strictly restrict returned schemes."""
    manager = VectorStoreManager(persist_dir=tmp_path / "chroma_filter_test", collection_name="filter_test")
    engine = SemanticSearchEngine(vector_store=manager)
    engine.ensure_indexed(force_refresh=True)

    # Search with Ministry filter
    results = engine.search(
        query="scholarship for student",
        top_k=5,
        where_filter={"ministry": "Ministry of Education"}
    )
    assert len(results) >= 1
    for r in results:
        assert r.ministry == "Ministry of Education"


def test_get_scheme_evidence(tmp_path):
    """Verify raw evidence and official URL retrieval for a scheme."""
    manager = VectorStoreManager(persist_dir=tmp_path / "chroma_evidence_test", collection_name="evidence_test")
    engine = SemanticSearchEngine(vector_store=manager)
    engine.ensure_indexed()

    evidence = engine.get_scheme_evidence("pm-kisan")
    assert evidence is not None
    assert evidence["scheme_id"] == "pm-kisan"
    assert "https://pmkisan.gov.in" in evidence["official_url"]
    assert "PM Kisan Samman Nidhi" in evidence["document"]
