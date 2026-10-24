"""测试环境配置。"""

import os
import tempfile
from pathlib import Path


# 页面冒烟测试会初始化模型客户端和 Chroma，但不发起网络请求。
os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")

_test_storage = Path(tempfile.gettempdir()) / "rag-agent-pytest"
os.environ.setdefault("CHROMA_PERSIST_DIRECTORY", str(_test_storage / "chroma"))
os.environ.setdefault("CHAT_HISTORY_DIRECTORY", str(_test_storage / "chat_history"))
os.environ.setdefault("MD5_STATE_PATH", str(_test_storage / "md5_text"))
