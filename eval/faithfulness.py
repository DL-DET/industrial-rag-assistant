"""答案忠实度判定：用 LLM 检查答案的结论能否被检索到的原文支持。

关键词覆盖率只能查“字有没有出现”，查不出方向说反、参数张冠李戴、
超资料补充这类逻辑错误。这里让模型拿答案和原文做一次独立复查。

注意：判定本身也是模型，会出错。它最大的价值是**找出可疑样本**，
不能当成绝对准确的正确率。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

import config_data as config
from eval.answer_metrics import is_refusal
from rag import format_documents


SYSTEM_PROMPT = """你是工业设备知识库的审核员。判断【答案】中的结论能否从【参考资料】找到直接依据。

判定规则：
1. 只判断答案是否有资料依据，不判断资料本身是否正确。
2. 数字、单位、方向词（不高于 / 至少 / 不大于 / 不超过）必须与资料一致，说反了算无依据。
3. 答案中超出资料范围的推测或补充说明，算无依据。
4. 如果答案是拒答（说明资料不足），supported 记为 true，理由写“拒答”。

只输出一个 JSON 对象，不要输出其他内容：
{"supported": true, "unsupported_claims": [], "reason": "一句话说明"}
"""

JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

logger = logging.getLogger(__name__)
_JUDGE_MODEL = None


@dataclass
class FaithfulnessResult:
    """supported 为 None 表示判定失败，调用方应单独统计，不要算作不忠实。"""

    supported: bool | None
    unsupported_claims: list[str] = field(default_factory=list)
    reason: str = ""


def _get_model() -> ChatTongyi:
    """判定模型复用同一个实例，避免每道题都重新建客户端。"""
    global _JUDGE_MODEL
    if _JUDGE_MODEL is None:
        config.ensure_dashscope_api_key()
        _JUDGE_MODEL = ChatTongyi(model=config.chat_model_name, streaming=False)
    return _JUDGE_MODEL


def build_prompt(question: str, answer: str, documents: list[Document]) -> str:
    return (
        f"【参考资料】\n{format_documents(documents)}\n\n"
        f"【问题】\n{question}\n\n"
        f"【答案】\n{answer}"
    )


def parse_judgement(text: str) -> FaithfulnessResult | None:
    """从模型输出里抽出 JSON；模型偶尔会加 ```json 包裹或前后说明文字。"""
    match = JSON_PATTERN.search(text)
    if match is None:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "supported" not in data:
        return None
    # 不能用 bool()：字符串 "false" 会被转成 True，把方向说反的答案判成忠实。
    supported = data["supported"]
    if isinstance(supported, str):
        normalized = supported.strip().lower()
        if normalized in {"true", "false"}:
            supported = normalized == "true"
    if not isinstance(supported, bool):
        return None

    claims = data.get("unsupported_claims") or []
    if not isinstance(claims, list):
        claims = [str(claims)]
    return FaithfulnessResult(
        supported=supported,
        unsupported_claims=[str(claim) for claim in claims],
        reason=str(data.get("reason", "")),
    )


def judge_faithfulness(
    question: str,
    answer: str,
    documents: list[Document],
    model=None,
) -> FaithfulnessResult:
    """判定答案是否被资料支持；拒答不参与判定。"""
    if is_refusal(answer):
        return FaithfulnessResult(supported=True, reason="拒答，无结论可判定")

    client = model if model is not None else _get_model()
    try:
        response = client.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=build_prompt(question, answer, documents)),
            ]
        )
    except Exception as exc:
        # 网络抖动或限流不能中断整轮评测：返回“判定失败”，由调用方单独统计。
        logger.warning("忠实度判定调用失败：%s", exc)
        return FaithfulnessResult(supported=None, reason=f"判定调用失败：{exc}")

    text = response.content if isinstance(response.content, str) else str(response.content)
    parsed = parse_judgement(text)
    if parsed is None:
        return FaithfulnessResult(supported=None, reason="判定输出无法解析")
    return parsed
