import pytest
from app.db.models.analysis_rule import AnalysisRule  # SQLAlchemy model


def test_analysis_rule_fields():
    rule = AnalysisRule(
        name="test",
        field="model_answer",
        condition={"type": "regex", "pattern": "error"},
        tags=["格式与规范错误.输出格式不符"],
        confidence=0.9,
        priority=10,
        is_active=True,
        created_by="admin",
    )
    assert rule.name == "test"
    assert rule.is_active is True
