from app.db.models import (
    User, EvalSession, EvalRecord, AnalysisResult,
    ErrorTag, AnalysisRule, AnalysisStrategy, PromptTemplate, Report,
)

def test_all_models_importable():
    assert User.__tablename__ == "users"
    assert EvalSession.__tablename__ == "eval_sessions"
    assert EvalRecord.__tablename__ == "eval_records"
    assert AnalysisResult.__tablename__ == "analysis_results"
    assert ErrorTag.__tablename__ == "error_tags"
    assert AnalysisRule.__tablename__ == "analysis_rules"
    assert AnalysisStrategy.__tablename__ == "analysis_strategies"
    assert PromptTemplate.__tablename__ == "prompt_templates"
    assert Report.__tablename__ == "reports"

def test_user_columns():
    cols = {c.name for c in User.__table__.columns}
    assert {"id", "username", "email", "password_hash", "role",
            "is_active", "created_at", "updated_at"}.issubset(cols)


def test_eval_record_has_jsonb_fields():
    cols = {c.name for c in EvalRecord.__table__.columns}
    assert "metadata" in cols
    assert "raw_json" in cols
