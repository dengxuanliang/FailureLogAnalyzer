from app.llm.output_parser import parse_llm_response


VALID_JSON = '''{
  "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂"],
  "root_cause": "推理链断裂",
  "severity": "high",
  "confidence": 0.8,
  "evidence": "证据",
  "suggestion": "建议"
}'''


def test_parse_valid_json():
    result = parse_llm_response(VALID_JSON)

    assert result.success is True
    assert result.output is not None
    assert result.output.root_cause == "推理链断裂"
    assert result.unmatched_tags == []


def test_parse_invalid_json_returns_error():
    raw = "this is not json"
    result = parse_llm_response(raw)

    assert result.success is False
    assert result.output is None
    assert result.raw_text == raw
    assert "JSON decode error" in result.error


def test_parse_markdown_wrapped_json_and_unknown_tag():
    raw = '''```json
{
  "error_types": ["推理性错误.逻辑推理错误.前提正确但推理链断裂", "不存在.标签"],
  "root_cause": "test",
  "severity": "medium",
  "confidence": 0.7,
  "evidence": "test",
  "suggestion": "test"
}
```'''

    result = parse_llm_response(raw)

    assert result.success is True
    assert result.output is not None
    assert result.unmatched_tags == ["不存在.标签"]
