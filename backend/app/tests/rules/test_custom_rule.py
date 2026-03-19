import pytest
import yaml
from app.rules.custom import CustomRule, CustomRuleEngine
from app.rules.base import RuleContext


def _ctx(**kwargs) -> RuleContext:
    defaults = dict(
        record_id="r1", model_answer="", expected_answer="",
        question="", extracted_code=None, metadata={},
    )
    defaults.update(kwargs)
    return RuleContext(**defaults)


# ---- YAML loading -------------------------------------------------------

SAMPLE_YAML = """
name: "syntax_error_detector"
description: "Detects Python syntax errors in answer"
field: "model_answer"
condition:
  type: "regex"
  pattern: "SyntaxError|IndentationError"
tags: ["格式与规范错误.输出格式不符"]
confidence: 0.9
priority: 10
"""


def test_load_from_yaml_dict():
    data = yaml.safe_load(SAMPLE_YAML)
    rule = CustomRule.from_dict(data)
    assert rule.rule_id == "syntax_error_detector"
    assert rule.priority == 10


# ---- regex --------------------------------------------------------------

def test_regex_fires_on_match():
    data = yaml.safe_load(SAMPLE_YAML)
    rule = CustomRule.from_dict(data)
    results = rule.evaluate(_ctx(model_answer="Got SyntaxError at line 3"))
    assert len(results) == 1
    assert results[0].tag_path == "格式与规范错误.输出格式不符"


def test_regex_silent_on_no_match():
    data = yaml.safe_load(SAMPLE_YAML)
    rule = CustomRule.from_dict(data)
    assert rule.evaluate(_ctx(model_answer="The answer is correct.")) == []


# ---- contains / not_contains -------------------------------------------

def test_contains_fires():
    data = {
        "name": "contains_test", "field": "model_answer",
        "condition": {"type": "contains", "value": "error"},
        "tags": ["生成质量问题.幻觉"], "confidence": 0.8,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(model_answer="There was an error."))) == 1


def test_not_contains_fires_when_absent():
    data = {
        "name": "not_contains_test", "field": "model_answer",
        "condition": {"type": "not_contains", "value": "hello"},
        "tags": ["生成质量问题.不完整回答"], "confidence": 0.7,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(model_answer="Good morning"))) == 1
    assert rule.evaluate(_ctx(model_answer="hello world")) == []


# ---- length_gt / length_lt ---------------------------------------------

def test_length_gt_fires():
    data = {
        "name": "too_long", "field": "model_answer",
        "condition": {"type": "length_gt", "value": 10},
        "tags": ["格式与规范错误.超长/截断回答"], "confidence": 0.75,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(model_answer="a" * 11))) == 1
    assert rule.evaluate(_ctx(model_answer="abc")) == []


def test_length_lt_fires():
    data = {
        "name": "too_short", "field": "model_answer",
        "condition": {"type": "length_lt", "value": 5},
        "tags": ["格式与规范错误.空回答/拒绝回答"], "confidence": 0.75,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(model_answer="Hi"))) == 1
    assert rule.evaluate(_ctx(model_answer="hello world")) == []


# ---- field_equals / field_missing --------------------------------------

def test_field_equals_on_metadata():
    data = {
        "name": "meta_check", "field": "metadata.difficulty",
        "condition": {"type": "field_equals", "value": "hard"},
        "tags": ["知识性错误.领域知识盲区"], "confidence": 0.6,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(metadata={"difficulty": "hard"}))) == 1
    assert rule.evaluate(_ctx(metadata={"difficulty": "easy"})) == []


def test_field_missing_fires_when_none():
    data = {
        "name": "extracted_missing", "field": "extracted_code",
        "condition": {"type": "field_missing"},
        "tags": ["解析类错误.代码提取为空"], "confidence": 0.85,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(extracted_code=None))) == 1
    assert rule.evaluate(_ctx(extracted_code="def foo(): pass")) == []


# ---- python_expr --------------------------------------------------------

def test_python_expr_fires():
    data = {
        "name": "custom_expr", "field": "model_answer",
        "condition": {"type": "python_expr", "expr": "len(value) > 5 and 'error' in value"},
        "tags": ["格式与规范错误.输出格式不符"], "confidence": 0.9,
    }
    rule = CustomRule.from_dict(data)
    assert len(rule.evaluate(_ctx(model_answer="syntax error found"))) == 1
    assert rule.evaluate(_ctx(model_answer="ok")) == []


# ---- CustomRuleEngine ---------------------------------------------------

def test_engine_loads_yaml_file(tmp_path):
    rules_yaml = """
rules:
  - name: "test_rule"
    field: "model_answer"
    condition:
      type: "contains"
      value: "crash"
    tags: ["格式与规范错误.JSON/代码块解析失败"]
    confidence: 0.8
"""
    f = tmp_path / "rules.yaml"
    f.write_text(rules_yaml)
    engine = CustomRuleEngine.from_yaml_file(str(f))
    assert len(engine.rules) == 1


def test_engine_evaluate_all():
    engine = CustomRuleEngine(rules=[])
    assert engine.evaluate_all(_ctx(model_answer="test")) == []
