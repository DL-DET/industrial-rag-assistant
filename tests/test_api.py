"""FastAPI 接口测试：用 Fake Service，不调用真实模型。"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

import api
import config_data as config
from observability import QueryTrace
from rag import REFUSAL_ANSWER


class FakeRagService:
    """只实现 API 用到的接口，避免测试依赖 Chroma 和 DashScope。"""

    def __init__(self, score: float = 0.9):
        self.score = score
        self.invoke_called = False
        self.stream_called = False
        self.recorded: list[tuple[str, str, str]] = []

    def retrieve_with_trace(self, question, trace_id=None, session_id=""):
        document = Document(
            page_content="离心风机应每季度检查润滑油。",
            metadata={"source": "manual.pdf", "page": 3},
        )
        trace = QueryTrace(
            trace_id=trace_id or "test-trace",
            session_id=session_id,
            query_chars=len(question),
        )
        trace.rerank_status = "success"
        trace.top_score = self.score
        trace.candidate_count = 1
        trace.returned_count = 1
        trace.top_sources = ["manual.pdf p.3"]
        return [document], trace

    def invoke_answer(self, question, session_id, documents=None):
        self.invoke_called = True
        return "应每季度检查润滑油。[资料 1]"

    def stream_answer(self, question, session_id, documents=None):
        self.stream_called = True
        yield "应每季度"
        yield "检查润滑油。[资料 1]"

    def record_turn(self, question, answer, session_id):
        self.recorded.append((question, answer, session_id))


@pytest.fixture(autouse=True)
def _stable_config(monkeypatch):
    """固定拒答阈值，关闭 trace 落盘，避免测试污染 logs/。"""
    monkeypatch.setattr(config, "refusal_enabled", True)
    monkeypatch.setattr(config, "refusal_score_threshold", 0.75)
    monkeypatch.setattr(config, "observability_enabled", False)


@pytest.fixture
def fake_service():
    return FakeRagService()


@pytest.fixture
def client(fake_service):
    api.app.dependency_overrides[api.get_rag_service] = lambda: fake_service
    with TestClient(api.app) as test_client:
        yield test_client
    api.app.dependency_overrides.clear()


def _event_names(body: str) -> list[str]:
    return [
        line.removeprefix("event: ")
        for line in body.splitlines()
        if line.startswith("event: ")
    ]


def test_health_returns_readiness(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert "api_key" in data
    assert "vector_store" in data


def test_chat_returns_answer_sources_and_citation(client, fake_service):
    response = client.post(
        "/chat",
        json={"question": "离心风机怎么保养？", "session_id": "test-chat"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "应每季度检查润滑油。[资料 1：manual.pdf]"
    assert data["sources"] == [
        {
            "source": "manual.pdf",
            "page": 3,
            "excerpt": "离心风机应每季度检查润滑油。",
        }
    ]
    assert data["refused"] is False
    assert data["trace_id"]
    assert fake_service.invoke_called is True


def test_chat_refuses_low_score_without_generation(client, fake_service):
    fake_service.score = 0.1

    response = client.post(
        "/chat",
        json={"question": "完全无关的问题", "session_id": "test-refusal"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["refused"] is True
    assert data["answer"] == REFUSAL_ANSWER
    assert fake_service.invoke_called is False
    assert fake_service.recorded


def test_chat_stream_emits_meta_delta_done(client, fake_service):
    with client.stream(
        "POST",
        "/chat/stream",
        json={"question": "离心风机怎么保养？", "session_id": "test-stream"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    events = _event_names(body)
    assert events[0] == "meta"
    assert events[-1] == "done"
    assert "delta" in events
    assert "manual.pdf" in body
    assert fake_service.stream_called is True


def test_chat_stream_refusal_has_no_delta(client, fake_service):
    fake_service.score = 0.1

    with client.stream(
        "POST",
        "/chat/stream",
        json={"question": "完全无关的问题", "session_id": "test-stream-refusal"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert _event_names(body) == ["meta", "done"]
    assert REFUSAL_ANSWER in body
    assert fake_service.stream_called is False


def test_empty_question_is_rejected(client):
    response = client.post("/chat", json={"question": ""})

    assert response.status_code == 422


def test_invalid_session_id_is_rejected(client):
    response = client.post(
        "/chat",
        json={"question": "离心风机怎么保养？", "session_id": "../bad"},
    )

    assert response.status_code == 400
