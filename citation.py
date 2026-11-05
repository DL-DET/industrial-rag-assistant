"""答案引用补全：把裸 [资料 N] 引用补成 [资料 N：文件名]。

提示词只能“建议”模型标注文件名，模型经常只写编号。
这里做确定性替换，保证每条引用都能追溯到具体文件。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from langchain_core.documents import Document


CITATION_PATTERN = re.compile(r"\[资料\s*(\d+)\]")
# 判断“模型已经写了文件名”时向后看的字数，够覆盖常见的“第 5 页”之类后缀。
LOOKAHEAD_CHARS = 40


def _source_map(documents: Iterable[Document]) -> dict[int, str]:
    """编号必须和 format_documents() 一致：从 1 开始按展开后的顺序编号。"""
    mapping: dict[int, str] = {}
    for index, document in enumerate(documents, start=1):
        source = str(document.metadata.get("source", "")).strip()
        if source:
            mapping[index] = source
    return mapping


def add_citations(answer: str, documents: Iterable[Document]) -> str:
    """把裸引用补成带文件名的形式；已经写了文件名的不重复添加。"""
    if not answer:
        return answer

    mapping = _source_map(documents)
    if not mapping:
        return answer

    def replace(match: re.Match[str]) -> str:
        number = int(match.group(1))
        source = mapping.get(number)
        if source is None:
            return match.group(0)
        tail = answer[match.end() : match.end() + LOOKAHEAD_CHARS]
        if source in tail:
            return match.group(0)
        return f"[资料 {number}：{source}]"

    return CITATION_PATTERN.sub(replace, answer)
