from langchain_core.documents import Document

import rag as rag_module
from file_history_store import FileChatMessageHistory
from rag import RagService, format_documents, resolve_page_number


def test_format_documents_contains_source_and_page():
    documents = [
        Document(
            page_content="轴承温度不应超过 80 摄氏度。",
            metadata={"source": "维护手册.pdf", "page": 12},
        )
    ]

    formatted = format_documents(documents)

    assert "维护手册.pdf" in formatted
    assert "第 12 页" in formatted
    assert "轴承温度不应超过 80 摄氏度。" in formatted


def test_format_empty_documents_returns_grounded_fallback():
    assert "没有检索到相关资料" in format_documents([])


def test_resolve_page_number_prefers_metadata():
    document = Document(
        page_content="[第 9 页]\n内容",
        metadata={"page": 3},
    )

    assert resolve_page_number(document) == 3


def test_resolve_page_number_falls_back_to_content_marker():
    document = Document(
        page_content="[第 7 页]\n内容",
        metadata={"source": "手册.pdf"},
    )

    assert resolve_page_number(document) == 7


def test_resolve_page_number_returns_none_without_marker():
    assert resolve_page_number(Document(page_content="内容", metadata={})) is None


def test_format_documents_uses_content_page_marker_fallback():
    formatted = format_documents(
        [
            Document(
                page_content="[第 5 页]\n轴承温度不应超过 80 摄氏度。",
                metadata={"source": "维护手册.pdf"},
            )
        ]
    )

    assert "第 5 页" in formatted


def test_stream_answer_saves_history_after_complete_response(tmp_path, monkeypatch):
    class FakeChain:
        def stream(self, inputs):
            assert inputs["history"] == []
            yield "风机需要定期维护。"

    history = FileChatMessageHistory("user_004", tmp_path)
    monkeypatch.setattr(rag_module, "get_history", lambda session_id: history)

    service = RagService.__new__(RagService)
    service.answer_chain = FakeChain()

    assert list(service.stream_answer("如何保养？", "user_004", [])) == [
        "风机需要定期维护。"
    ]
    assert [message.content for message in history.messages] == [
        "如何保养？",
        "风机需要定期维护。",
    ]
