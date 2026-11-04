"""拒答路由测试：只认重排分，降级路径一律不判断。"""

import config_data as config
from eval.answer_metrics import is_refusal
from observability import QueryTrace
from rag import REFUSAL_ANSWER, should_refuse


def _trace(score, status="success"):
    return QueryTrace(trace_id="t1", rerank_status=status, top_score=score)


def _enable(monkeypatch, threshold=0.75):
    monkeypatch.setattr(config, "refusal_enabled", True)
    monkeypatch.setattr(config, "refusal_score_threshold", threshold)


def test_refuses_when_score_below_threshold(monkeypatch):
    _enable(monkeypatch)
    assert should_refuse(_trace(0.50)) is True


def test_answers_when_score_above_threshold(monkeypatch):
    _enable(monkeypatch)
    assert should_refuse(_trace(0.90)) is False


def test_threshold_boundary_still_answers(monkeypatch):
    """等于阈值不拒答：用小于比较，避免分数轻微抖动就误伤真实问题。"""
    _enable(monkeypatch)
    assert should_refuse(_trace(0.75)) is False


def test_fallback_never_refuses(monkeypatch):
    """降级时 top_score 是向量相似度，和重排分不是一把尺子。"""
    _enable(monkeypatch)
    assert should_refuse(_trace(0.10, status="fallback")) is False


def test_circuit_open_never_refuses(monkeypatch):
    _enable(monkeypatch)
    assert should_refuse(_trace(0.10, status="circuit_open")) is False


def test_empty_candidates_never_refuses(monkeypatch):
    _enable(monkeypatch)
    assert should_refuse(_trace(None, status="empty")) is False


def test_disabled_status_never_refuses(monkeypatch):
    """关闭重排时同样没有重排分，不能套用阈值。"""
    _enable(monkeypatch)
    assert should_refuse(_trace(0.10, status="disabled")) is False


def test_missing_score_never_refuses(monkeypatch):
    _enable(monkeypatch)
    assert should_refuse(_trace(None)) is False


def test_switch_off_never_refuses(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(config, "refusal_enabled", False)
    assert should_refuse(_trace(0.10)) is False


def test_refusal_answer_is_recognized_by_metrics():
    """拒答文案必须能被评测脚本识别，否则误拒率统计会失真。"""
    assert is_refusal(REFUSAL_ANSWER) is True
