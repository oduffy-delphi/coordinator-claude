"""Experiment harness for LLM code review experiments.

Shared infrastructure used by both the persona and sequential experiments:
- client: Anthropic SDK wrapper with retry + cost tracking
- parser: JSON response extraction with repair fallback
- scorer: Bipartite matching of findings against defect/distractor manifests
- storage: SQLite persistence with checkpoint/resume
- corpus: Corpus loading and validation (YAML/JSON manifests)
- schemas: Pydantic data contracts for all data flows
"""

from .client import ExperimentClient
from .corpus import Corpus
from .parser import ParseResult, parse_review_response
from .schemas import (
    APICallRecord,
    DefectEntry,
    DefectManifest,
    DistractorEntry,
    DistractorManifest,
    FileScore,
    FindingClassification,
    MatchMethod,
    ReviewFinding,
    ReviewOutput,
    ScoredFinding,
)
from .scorer import ScoredReview, score_review
from .storage import ExperimentDB

__all__ = [
    "ExperimentClient",
    "ExperimentDB",
    "Corpus",
    "ParseResult",
    "parse_review_response",
    "ScoredReview",
    "score_review",
    "APICallRecord",
    "DefectEntry",
    "DefectManifest",
    "DistractorEntry",
    "DistractorManifest",
    "FileScore",
    "FindingClassification",
    "MatchMethod",
    "ReviewFinding",
    "ReviewOutput",
    "ScoredFinding",
]
