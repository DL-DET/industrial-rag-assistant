from langchain_core.documents import Document

import rag as rag_module
from file_history_store import FileChatMessageHistory
from rag import RagService, format_documents


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
