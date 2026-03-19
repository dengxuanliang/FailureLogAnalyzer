import json
import pytest
from pathlib import Path
from app.ingestion.parsers import parse_jsonl, parse_large_json


@pytest.fixture
def jsonl_file(tmp_path):
    lines = [
        {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
         "model_answer": "B", "is_correct": i % 2 == 0}
        for i in range(5)
    ]
    p = tmp_path / "data.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines))
    return str(p)


def test_parse_jsonl_yields_all_records(jsonl_file):
    records = list(parse_jsonl(jsonl_file))
    assert len(records) == 5
    assert records[0]["question_id"] == "q0"


def test_parse_jsonl_skips_blank_lines(tmp_path):
    p = tmp_path / "gaps.jsonl"
    p.write_text('\n{"question_id":"a","is_correct":true}\n\n{"question_id":"b","is_correct":false}\n')
    records = list(parse_jsonl(str(p)))
    assert len(records) == 2


def test_parse_jsonl_skips_corrupt_lines(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"question_id":"a","is_correct":true}\nNOT_JSON\n{"question_id":"b","is_correct":false}\n')
    records = list(parse_jsonl(str(p)))
    assert len(records) == 2  # corrupt line skipped


@pytest.fixture
def large_json_file(tmp_path):
    data = [
        {"question_id": f"q{i}", "question": f"Q{i}", "expected_answer": "A",
         "model_answer": "B", "is_correct": False}
        for i in range(4)
    ]
    p = tmp_path / "big.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_parse_large_json_yields_all_items(large_json_file):
    records = list(parse_large_json(large_json_file))
    assert len(records) == 4
    assert records[2]["question_id"] == "q2"
