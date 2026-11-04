import json

import config_data as config
from observability import QueryTrace, write_trace


def test_write_trace_appends_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "qa.jsonl"
    monkeypatch.setattr(config, "observability_enabled", True)

    first = QueryTrace(trace_id="t1", candidate_count=10, returned_count=3)
    second = QueryTrace(trace_id="t2", fallback=True, rerank_status="fallback")
    write_trace(first, path=log_path)
    write_trace(second, path=log_path)

    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
    ]

    assert [record["trace_id"] for record in records] == ["t1", "t2"]
    assert records[0]["candidate_count"] == 10
    assert records[1]["fallback"] is True
    assert "question" not in records[0]


def test_write_trace_respects_disabled_switch(tmp_path, monkeypatch):
    log_path = tmp_path / "qa.jsonl"
    monkeypatch.setattr(config, "observability_enabled", False)

    write_trace(QueryTrace(trace_id="t1"), path=log_path)

    assert not log_path.exists()
