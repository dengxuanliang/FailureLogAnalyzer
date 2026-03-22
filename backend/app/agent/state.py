"""Orchestrator Agent shared state definition."""
from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict


class Message(TypedDict):
    role: str
    content: str


class OrchestratorState(TypedDict):
    user_input: str
    intent: str
    conversation_history: Annotated[list[Message], operator.add]

    ingest_job_id: Optional[str]
    ingest_status: Optional[str]

    target_session_ids: list[str]
    target_filters: dict
    analysis_strategy: str

    rule_job_id: Optional[str]
    llm_job_id: Optional[str]
    rule_summary: Optional[dict]
    llm_summary: Optional[dict]
    analyzed_count: int
    total_count: int

    report_id: Optional[str]
    report_status: Optional[str]

    current_step: str
    errors: Annotated[list[str], operator.add]
    needs_human_input: bool


def create_initial_state(user_input: str = "") -> OrchestratorState:
    return OrchestratorState(
        user_input=user_input,
        intent="",
        conversation_history=[],
        ingest_job_id=None,
        ingest_status=None,
        target_session_ids=[],
        target_filters={},
        analysis_strategy="fallback",
        rule_job_id=None,
        llm_job_id=None,
        rule_summary=None,
        llm_summary=None,
        analyzed_count=0,
        total_count=0,
        report_id=None,
        report_status=None,
        current_step="start",
        errors=[],
        needs_human_input=False,
    )
