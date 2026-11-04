"""规则式多部分问题拆解。

先覆盖两类高频问题：
1. “原因 + 处理方法”
2. “A 和 B 分别是多少 / 是什么”

拆不出来时原样返回，避免引入额外风险。
"""

from __future__ import annotations

import re


_CAUSE_ACTION_PATTERNS = [
    re.compile(
        r"^(?P<subject>.+?)(?:有哪些)?原因(?:有哪些)?[，,、]?"
        r"(?:如何|怎么|怎样)?(?:处理|解决|排查)(?:方法)?(?:是什么)?$"
    ),
    re.compile(
        r"^(?P<subject>.+?)的原因(?:和|及|与)"
        r"(?:处理|解决|排查)(?:方法)?(?:是什么)?$"
    ),
]

_MULTI_PART_PATTERN = re.compile(
    r"^(?P<subject>.+?)的(?P<parts>[^？?]+?)"
    r"(?:分别是|分别|是多少|是什么|有哪些)(?:[？?])?$"
)

_PART_SEPARATOR = re.compile(r"以及|、|和|及|与")


def decompose_question(question: str, max_parts: int = 3) -> list[str]:
    """把多部分问题拆成子问题；无法识别时返回原问题。"""
    text = question.strip().rstrip("？?")
    if not text:
        return [question]

    for pattern in _CAUSE_ACTION_PATTERNS:
        match = pattern.match(text)
        if match:
            subject = match.group("subject").strip()
            if not subject:
                continue
            return [
                f"{subject}的原因有哪些？",
                f"{subject}的处理方法是什么？",
            ][:max_parts]

    match = _MULTI_PART_PATTERN.match(text)
    if match:
        subject = match.group("subject").strip()
        parts = [
            part.strip()
            for part in _PART_SEPARATOR.split(match.group("parts"))
            if part.strip()
        ]
        if subject and 2 <= len(parts) <= max_parts:
            return [f"{subject}的{part}是多少？" for part in parts]

    return [question]
