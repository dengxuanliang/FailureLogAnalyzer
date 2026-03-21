import pytest

from app.schemas.llm import LlmJobTriggerRequest, StrategyCreate


def test_strategy_create_validates_positive_budget():
    with pytest.raises(ValueError):
        StrategyCreate(
            name="s1",
            strategy_type="full",
            llm_provider="openai",
            llm_model="gpt-4o",
            daily_budget=-1,
        )


def test_llm_job_trigger_manual_ids_required_for_manual_strategy():
    with pytest.raises(ValueError):
        LlmJobTriggerRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            strategy_id="00000000-0000-0000-0000-000000000002",
            manual_record_ids=[],
            expect_manual_records=True,
        )
