from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

import rerank
from rerank import RerankService


def _response(results, status_code=200):
    return SimpleNamespace(
        status_code=status_code,
        code=None,
        message=None,
        output=SimpleNamespace(results=results),
    )


def test_rerank_maps_indices_and_scores(monkeypatch):
    documents = [
        Document(page_content="文档 A"),
        Document(page_content="文档 B"),
        Document(page_content="文档 C"),
    ]
    response = _response(
        [
            {"index": 2, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.5},
        ]
    )

    monkeypatch.setattr(rerank.TextReRank, "call", lambda **kwargs: response)
    service = RerankService(model="test-model")

    result = service.rerank("问题", documents, top_n=2)

    assert [document.page_content for document, _ in result] == ["文档 C", "文档 A"]
    assert [score for _, score in result] == [0.9, 0.5]


def test_rerank_empty_documents_skips_api(monkeypatch):
    def fail_call(**kwargs):
        raise AssertionError("空文档不应调用重排 API")

    monkeypatch.setattr(rerank.TextReRank, "call", fail_call)

    assert RerankService(model="test-model").rerank("问题", []) == []


def test_rerank_raises_on_api_error(monkeypatch):
    response = _response([], status_code=500)
    monkeypatch.setattr(rerank.TextReRank, "call", lambda **kwargs: response)

    with pytest.raises(RuntimeError, match="重排失败"):
        RerankService(model="test-model").rerank(
            "问题",
            [Document(page_content="文档")],
        )
