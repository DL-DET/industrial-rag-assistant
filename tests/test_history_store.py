import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from file_history_store import FileChatMessageHistory


def test_history_round_trip_and_clear(tmp_path):
    history = FileChatMessageHistory("user_001", tmp_path)
    history.add_messages(
        [
            HumanMessage(content="风机如何保养？"),
            AIMessage(content="请定期检查轴承润滑。"),
        ]
    )

    assert [message.content for message in history.messages] == [
        "风机如何保养？",
        "请定期检查轴承润滑。",
    ]

    history.clear()
    assert history.messages == []


@pytest.mark.parametrize(
    "session_id",
    ["../secret", "user/001", "", "会话一号"],
)
def test_invalid_session_id_is_rejected(tmp_path, session_id):
    with pytest.raises(ValueError, match="session_id"):
        FileChatMessageHistory(session_id, tmp_path)


def test_corrupted_history_raises_clear_error(tmp_path):
    history = FileChatMessageHistory("user_002", tmp_path)
    history.file_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(RuntimeError, match="会话历史文件损坏"):
        _ = history.messages


def test_history_is_saved_as_utf8_json(tmp_path):
    history = FileChatMessageHistory("user_003", tmp_path)
    history.add_messages([HumanMessage(content="中文内容")])

    payload = json.loads(history.file_path.read_text(encoding="utf-8"))

    assert payload[0]["data"]["content"] == "中文内容"
