"""Tests for OrchestratorState TypedDict validation."""
import typing

from app.agent.state import OrchestratorState, create_initial_state


def test_create_initial_state_has_required_fields() -> None:
    state = create_initial_state()
    assert state["user_input"] == ""
    assert state["intent"] == ""
    assert state["conversation_history"] == []
    assert state["current_step"] == "start"
    assert state["errors"] == []
    assert state["needs_human_input"] is False
    assert state["analyzed_count"] == 0
    assert state["total_count"] == 0


def test_create_initial_state_with_user_input() -> None:
    state = create_initial_state(user_input="分析一下 mmlu 的错题")
    assert state["user_input"] == "分析一下 mmlu 的错题"


def test_state_can_be_updated() -> None:
    state = create_initial_state()
    state["intent"] = "analyze"
    state["current_step"] = "rule_analysis"
    assert state["intent"] == "analyze"
    assert state["current_step"] == "rule_analysis"


def test_state_has_annotated_list_fields() -> None:
    """Verify that list fields use Annotated reducers for LangGraph."""
    hints = typing.get_type_hints(OrchestratorState, include_extras=True)
    for field in ("conversation_history", "errors"):
        assert hasattr(hints[field], "__metadata__"), (
            f"{field} should use Annotated with a reducer for LangGraph"
        )
