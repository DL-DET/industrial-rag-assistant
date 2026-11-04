from langchain_core.documents import Document

from hybrid import (
    BM25Index,
    HybridRetriever,
    reciprocal_rank_fusion,
    tokenize,
)


def _doc(text: str, source: str = "手册.pdf") -> Document:
    return Document(page_content=text, metadata={"source": source})


def test_tokenize_keeps_chinese_and_english_terms():
    tokens = tokenize("WL 污水泵无法启动，检查电源缺相")

    assert "wl" in tokens
    assert "污水泵" in tokens
    assert "启动" in tokens
    assert "，" not in tokens


def test_bm25_prefers_exact_term_match():
    documents = [
        _doc("WL 污水泵无法启动，检查电源缺相和叶轮卡死。"),
        _doc("离心泵的日常维护与保养方法。"),
        _doc("风机轴承温度过高的处理步骤。"),
        _doc("PLC 控制柜的巡检要求。"),
        _doc("减速机漏油的常见原因。"),
    ]
    index = BM25Index(documents)

    results = index.search("污水泵无法启动", k=2)

    assert results
    assert results[0][0].page_content.startswith("WL 污水泵")


def test_bm25_empty_index_returns_empty():
    assert BM25Index([]).search("任意问题", k=3) == []


def test_rrf_prefers_document_ranked_high_in_both_lists():
    a = _doc("文档 A")
    b = _doc("文档 B")
    c = _doc("文档 C")

    fused = reciprocal_rank_fusion(
        [
            [(a, 0.9), (b, 0.8), (c, 0.7)],
            [(c, 10.0), (a, 9.0), (b, 8.0)],
        ],
        k=60,
    )

    assert fused[0][0].page_content == "文档 A"
    assert len(fused) == 3


def test_rrf_deduplicates_same_document():
    document = _doc("同一片段")

    fused = reciprocal_rank_fusion(
        [[(document, 0.9)], [(document, 12.0)]],
        k=60,
    )

    assert len(fused) == 1
    assert fused[0][0].page_content == "同一片段"
    assert fused[0][1] == 1 / 61 + 1 / 61


class FakeVectorService:
    def __init__(self, documents):
        self.documents = documents
        self.search_calls = []

    def all_documents(self):
        return self.documents

    def search_with_scores(self, query, k=None):
        self.search_calls.append((query, k))
        return [(document, 0.9) for document in self.documents[:k]]


def test_hybrid_falls_back_to_vector_when_bm25_has_no_match():
    documents = [_doc("完全无关的维护说明", "a.pdf")]
    vector_service = FakeVectorService(documents)
    retriever = HybridRetriever(vector_service)

    results = retriever.search("量子力学", k=3)

    assert [document.page_content for document, _ in results] == [
        document.page_content for document in documents
    ]
    assert vector_service.search_calls == [("量子力学", 3)]
