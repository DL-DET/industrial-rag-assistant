"""项目统一配置。

路径默认基于当前文件所在目录生成，避免把开发机上的绝对路径写死在代码里。
敏感配置统一从环境变量或项目根目录的 .env 文件读取。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _read_positive_int(name: str, default: int) -> int:
    """读取正整数环境变量，并在配置错误时尽早给出明确提示。"""
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数，当前值为：{raw_value}") from exc
    if value <= 0:
        raise ValueError(f"环境变量 {name} 必须大于 0，当前值为：{value}")
    return value


def _read_path(name: str, default: Path) -> Path:
    """读取路径配置；相对路径统一转换为相对于项目根目录的绝对路径。"""
    path = Path(os.getenv(name, str(default))).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def ensure_dashscope_api_key() -> None:
    """在创建模型客户端前检查密钥，避免到请求阶段才出现难懂的报错。"""
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError(
            "未配置 DASHSCOPE_API_KEY。请复制 .env.example 为 .env，"
            "或在终端中设置该环境变量。"
        )


# 本地持久化路径
persist_directory = _read_path("CHROMA_PERSIST_DIRECTORY", PROJECT_ROOT / "chroma_db")
md5_path = _read_path("MD5_STATE_PATH", PROJECT_ROOT / "md5_text")
chat_history_directory = _read_path(
    "CHAT_HISTORY_DIRECTORY",
    PROJECT_ROOT / "chat_history",
)

# Chroma 配置
collection_name = os.getenv("CHROMA_COLLECTION_NAME", "rag")

# 文本分块配置
chunk_size = _read_positive_int("CHUNK_SIZE", 300)
chunk_overlap = _read_positive_int("CHUNK_OVERLAP", 50)
if chunk_overlap >= chunk_size:
    raise ValueError("CHUNK_OVERLAP 必须小于 CHUNK_SIZE")
separators = ["\n\n", "\n", "\t", " ", ".", "!", "?", ",", "。", ""]
max_split_char_number = _read_positive_int("MAX_SPLIT_CHAR_NUMBER", 1000)

# 检索与模型配置
retrieval_top_k = _read_positive_int("RETRIEVAL_TOP_K", 3)
max_history_messages = _read_positive_int("MAX_HISTORY_MESSAGES", 20)
embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v4")
chat_model_name = os.getenv("CHAT_MODEL_NAME", "qwen-max")

# 上传限制
max_upload_size_mb = _read_positive_int("MAX_UPLOAD_SIZE_MB", 10)


def runtime_readiness() -> dict[str, bool]:
    """返回本地运行条件，供界面显示真实状态而不是写死的“在线”。"""
    return {
        "api_key": bool(os.getenv("DASHSCOPE_API_KEY", "").strip()),
        "vector_store": persist_directory.exists(),
    }
