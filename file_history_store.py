"""基于本地 JSON 文件的轻量聊天历史存储。"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

import config_data as config


# session_id 会参与文件名拼接，因此只允许安全的字母、数字、下划线和短横线。
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def get_history(session_id: str) -> "FileChatMessageHistory":
    return FileChatMessageHistory(session_id, config.chat_history_directory)


class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str, storage_path: str | Path):
        if not _SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError("session_id 只能包含字母、数字、下划线和短横线，长度 1-80")

        self.session_id = session_id
        self.storage_path = Path(storage_path)
        self.file_path = self.storage_path / session_id
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _write_messages(self, messages: Sequence[BaseMessage]) -> None:
        """先写临时文件再原子替换，避免进程中断后留下半截 JSON。"""
        payload = [message_to_dict(message) for message in messages]
        temporary_path = self.file_path.with_name(
            f"{self.file_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary_path, self.file_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        all_messages = list(self.messages)
        all_messages.extend(messages)
        self._write_messages(all_messages)

    @property
    def messages(self) -> list[BaseMessage]:
        if not self.file_path.exists():
            return []

        try:
            messages_data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return messages_from_dict(messages_data)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"会话历史文件损坏：{self.file_path}，请清理该会话后重试"
            ) from exc

    def clear(self) -> None:
        self._write_messages([])
