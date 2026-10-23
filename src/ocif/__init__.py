"""Obsidian Content Intelligence & Factory core consumer primitives."""

from .ingestion import CONTRACT_VERSION, ContractError, ImportResult, OCIFStore, validate_envelope
from .postgres_store import PostgresOCIFStore
from .retrieval import build_index, evaluate_retrieval, evidence_linked_brief, retrieve

__all__ = [
    "CONTRACT_VERSION", "ContractError", "ImportResult", "OCIFStore", "PostgresOCIFStore",
    "validate_envelope", "build_index", "evaluate_retrieval",
    "evidence_linked_brief", "retrieve",
]
