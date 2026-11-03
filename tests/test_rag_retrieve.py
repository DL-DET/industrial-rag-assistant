import logging

from langchain_core.documents import Document

import config_data as config
from rag import RagService


def _doc(name: str) -> Document:
    return Document(page_content=name, metadata={"source": f"{name}.pdf"})


class FakeVectorService:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.calls: list[tuple[str, int | None]] = []

    def search_with_scores(self, query: str, k: int | None = None):
        self.calls.append((query, k))
        return [(document, 0.5) for document in self.documents]


class FakeReranker:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result or []
        self.error = error
        self.calls: list[tuple[str, list[Document], int | None]] = []

    def rerank(self, query, documents, top_n=None):
        self.calls.append((query, documents, top_n))
        if self.error is not None:
            raise self.error
        return self.result


class FakeRetriever:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.calls: list[str] = []

    def invoke(self, question: str):
        self.calls.append(question)
        return self.documents


def _make_service(reranker, vector_service=None, retriever=None):
    service = RagService.__new__(RagService)
    service.reranker = reranker
    service.vector_service = vector_service
    service.retriever = retriever
    return service


def test_retrieve_returns_reranked_order(monkeypatch):
    documents = [_doc(name) for name in "ABCD"]
    vector_service = FakeVectorService(documents)
    reranker = FakeReranker([(documents[2], 0.9), (documents[0], 0.8)])
    service = _make_service(reranker, vector_service=vector_service)
    monkeypatch.setattr(config, "rerank_candidate_k", 10)
    monkeypatch.setattr(config, "rerank_top_n", 2)

    result = service.retrieve("问题")

    assert [document.page_content for document in result] == ["C", "A"]
    assert vector_service.calls == [("问题", 10)]
    assert reranker.calls[0][0] == "问题"
    assert reranker.calls[0][2] == 2


def test_retrieve_falls_back_to_vector_top_k_when_rerank_fails(
    monkeypatch, caplog
):
    documents = [_doc(name) for name in "ABCDE"]
    vector_service = FakeVectorService(documents)
    reranker = FakeReranker(error=RuntimeError("重排服务超时"))
    service = _make_service(reranker, vector_service=vector_service)
    monkeypatch.setattr(config, "retrieval_top_k", 3)

    with caplog.at_level(logging.ERROR):
        result = service.retrieve("问题")

    assert [document.page_content for document in result] == ["A", "B", "C"]
    assert "重排失败" in caplog.text


def test_retrieve_returns_empty_without_candidates(monkeypatch):
    vector_service = FakeVectorService([])
    reranker = FakeReranker(error=AssertionError("空候选不应调用重排"))
    service = _make_service(reranker, vector_service=vector_service)
    monkeypatch.setattr(config, "rerank_candidate_k", 10)

    assert service.retrieve("问题") == []
    assert reranker.calls == []


def test_retrieve_skips_rerank_when_disabled():
    documents = [_doc("A"), _doc("B")]
    retriever = FakeRetriever(documents)
    service = _make_service(None, retriever=retriever)

    result = service.retrieve("问题")

    assert [document.page_content for document in result] == ["A", "B"]
    assert retriever.calls == ["问题"]
