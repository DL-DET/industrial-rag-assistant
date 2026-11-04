"""结构感知的父子块切分。

child 约 300 字，用于检索和重排；parent 约 800 字，用于生成上下文。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config


_PAGE_MARKER_PATTERN = re.compile(r"\[第\s*(\d+)\s*页\]")
_HEADING_PATTERN = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\s+(?P<title>[^|\n]{2,60})$")
_EXCLUDED_TITLE_TOKENS = (
    "kW",
    "mm",
    "℃",
    "m/s",
    "t/h",
    "r/min",
    "m³",
    "%",
    "Pa",
    "小时",
    "个月",
    "kg",
    "字；",
    "字，",
)
_TOC_DOTS = re.compile(r"\.{4,}")
_DATE_TITLE = re.compile(r"\d{4}\s*年")
_NOISE_MARKERS = (
    "用途与入库建议",
    "使用建议",
    "单块建议",
    "入库时可按",
    "向量化可使用",
    "ChromaDB 本地持久化存储",
)


@dataclass(frozen=True)
class Section:
    heading: str
    body: str


def split_text_by_page(text: str) -> list[tuple[int | None, str]]:
    """按 PDF 页码标记切分文本，返回 [(页码, 正文), ...]。"""
    matches = list(_PAGE_MARKER_PATTERN.finditer(text))
    if not matches:
        stripped = text.strip()
        return [(None, stripped)] if stripped else []

    sections: list[tuple[int | None, str]] = []
    preface = text[: matches[0].start()].strip()
    if preface:
        sections.append((None, preface))

    for index, match in enumerate(matches):
        page = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page_text = text[match.end() : end].strip()
        if page_text:
            sections.append((page, page_text))
    return sections


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if _DATE_TITLE.search(stripped):
        return False
    match = _HEADING_PATTERN.match(stripped)
    if not match:
        return False
    title = match.group("title").strip()
    if not re.search(r"[A-Za-z一-鿿]", title):
        return False
    return not any(token in title for token in _EXCLUDED_TITLE_TOKENS)


def _is_noise_body(body: str) -> bool:
    """过滤目录、封面、前言和入库建议等非知识内容。"""
    stripped = body.strip()
    if not stripped:
        return True
    if stripped.startswith(("目 录", "目录")):
        return True
    if _TOC_DOTS.search(stripped):
        return True
    if stripped.startswith("工业设备 RAG 知识库文本资料汇编"):
        return True
    return any(marker in stripped for marker in _NOISE_MARKERS)


def _looks_like_table(text: str) -> bool:
    return sum(1 for line in text.splitlines() if "|" in line) >= 2


def _split_table_children(text: str, max_chars: int) -> list[str]:
    """按行切表格，并在每个 child 中重复表头。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    table_index = next(
        (index for index, line in enumerate(lines) if "|" in line),
        None,
    )
    if table_index is None:
        return [text]

    prefix = lines[:table_index]
    header = lines[table_index]
    rows = lines[table_index + 1 :]
    children: list[str] = []
    current = [*prefix, header]
    current_length = sum(len(line) + 1 for line in current)

    for row in rows:
        if len(current) > 1 and current_length + len(row) + 1 > max_chars:
            children.append("\n".join(current))
            current = [header, row]
            current_length = len(header) + len(row) + 2
        else:
            current.append(row)
            current_length += len(row) + 1

    if current:
        children.append("\n".join(current))
    return children


def split_sections(text: str) -> list[Section]:
    """按章节标题切分；没有标题时整段作为一个 section。"""
    sections: list[Section] = []
    heading = ""
    body: list[str] = []

    def flush() -> None:
        nonlocal heading, body
        body_text = "\n".join(body).strip()
        if heading or body_text:
            sections.append(Section(heading=heading, body=body_text))
        heading = ""
        body = []

    for line in text.splitlines():
        if _is_heading(line):
            flush()
            heading = line.strip()
        else:
            body.append(line)
    flush()
    return sections


def _make_splitters(
    child_splitter: RecursiveCharacterTextSplitter | None = None,
    parent_splitter: RecursiveCharacterTextSplitter | None = None,
) -> tuple[RecursiveCharacterTextSplitter, RecursiveCharacterTextSplitter]:
    child = child_splitter or RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=config.separators,
        length_function=len,
    )
    parent = parent_splitter or RecursiveCharacterTextSplitter(
        chunk_size=config.parent_chunk_size,
        chunk_overlap=config.parent_chunk_overlap,
        separators=config.separators,
        length_function=len,
    )
    return child, parent


def build_parent_child_documents(
    text: str,
    source: str,
    doc_id: str,
    create_time: str,
    version: int = 1,
    updated_at: str | None = None,
    child_splitter: RecursiveCharacterTextSplitter | None = None,
    parent_splitter: RecursiveCharacterTextSplitter | None = None,
) -> list[Document]:
    """把文本切成 child 文档，并在 metadata 中保存 parent 文本。"""
    child_splitter, parent_splitter = _make_splitters(child_splitter, parent_splitter)
    documents: list[Document] = []

    for page, page_text in split_text_by_page(text):
        sections = split_sections(page_text)
        for section_index, section in enumerate(sections):
            if _is_noise_body(section.body):
                continue
            section_text = (
                f"{section.heading}\n{section.body}".strip()
                if section.heading
                else section.body.strip()
            )
            if not section_text:
                continue

            parent_parts = (
                [section_text]
                if _looks_like_table(section_text)
                else parent_splitter.split_text(section_text)
            )
            for parent_index, parent_part in enumerate(parent_parts):
                parent_text = parent_part.strip()
                if not parent_text:
                    continue
                if section.heading and section.heading not in parent_text:
                    parent_text = f"{section.heading}\n{parent_text}"

                parent_id = (
                    f"{doc_id}-{page if page is not None else 'none'}-"
                    f"{section_index}-{parent_index}"
                )
                children = (
                    _split_table_children(parent_text, config.chunk_size)
                    if _looks_like_table(parent_text)
                    else child_splitter.split_text(parent_text)
                )
                for child_text in children:
                    child_text = child_text.strip()
                    if not child_text:
                        continue
                    if section.heading and section.heading not in child_text:
                        child_text = f"{section.heading}\n{child_text}"

                    metadata: dict[str, object] = {
                        "source": source,
                        "doc_id": doc_id,
                        "version": version,
                        "updated_at": updated_at or create_time,
                        "create_time": create_time,
                        "section": section.heading,
                        "parent_id": parent_id,
                        "parent_text": parent_text,
                    }
                    if page is not None:
                        metadata["page"] = page
                    documents.append(
                        Document(page_content=child_text, metadata=metadata)
                    )
    return documents


def expand_parent_documents(documents: Iterable[Document]) -> list[Document]:
    """把 child 文档展开为 parent，并按 parent_id 去重。"""
    expanded: list[Document] = []
    seen: set[str] = set()
    for document in documents:
        parent_id = document.metadata.get("parent_id")
        parent_text = document.metadata.get("parent_text")
        if parent_id and parent_text:
            key = str(parent_id)
            if key in seen:
                continue
            seen.add(key)
            metadata = {
                key_name: value
                for key_name, value in document.metadata.items()
                if key_name != "parent_text"
            }
            expanded.append(Document(page_content=str(parent_text), metadata=metadata))
        else:
            expanded.append(document)
    return expanded


def expand_parent_pairs(
    pairs: Iterable[tuple[Document, float]],
) -> list[tuple[Document, float]]:
    """展开 parent 并保留原排序分数。"""
    expanded: list[tuple[Document, float]] = []
    seen: set[str] = set()
    for document, score in pairs:
        parent_id = document.metadata.get("parent_id")
        parent_text = document.metadata.get("parent_text")
        if parent_id and parent_text:
            key = str(parent_id)
            if key in seen:
                continue
            seen.add(key)
            metadata = {
                key_name: value
                for key_name, value in document.metadata.items()
                if key_name != "parent_text"
            }
            expanded.append(
                (Document(page_content=str(parent_text), metadata=metadata), score)
            )
        else:
            expanded.append((document, score))
    return expanded
