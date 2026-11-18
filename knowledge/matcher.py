"""Scheme Matcher combining candidate retrieval with deterministic rule execution."""

from knowledge.retriever import SchemeRetriever
from knowledge.rule_engine import evaluate_all
from shared.schemas import CitizenProfile, MatchResult


class SchemeMatcher:
    """Orchestrates candidate scheme filtering and deterministic rule evaluation."""

    def __init__(self, retriever: SchemeRetriever = None):
        self.retriever = retriever or SchemeRetriever()

    def match(self, profile: CitizenProfile, query: str = "") -> list[MatchResult]:
        """Runs candidate retrieval followed by deterministic rule engine."""
        candidates = self.retriever.filter_candidates(profile=profile, query=query)
        return evaluate_all(profile=profile, schemes=candidates)
