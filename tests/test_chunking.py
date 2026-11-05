from langchain_core.documents import Document

from chunking import (
    build_parent_child_documents,
    expand_parent_documents,
    expand_parent_pairs,
    split_sections,
    split_text_by_page,
)


def test_split_sections_by_heading():
    sections = split_sections("前言\n1 设备概述\n甲\n1.1 参数\n乙")

    assert [(section.heading, section.body) for section in sections] == [
        ("", "前言"),
        ("1 设备概述", "甲"),
        ("1.1 参数", "乙"),
    ]


def test_heading_filter_ignores_table_values():
    sections = split_sections("1.6 m/s\n30 kW\n1 设备概述\n甲")

    assert [(section.heading, section.body) for section in sections] == [
        ("", "1.6 m/s\n30 kW"),
        ("1 设备概述", "甲"),
    ]


def test_split_text_by_page_keeps_page_numbers():
    assert split_text_by_page("前言\n[第 1 页]\n甲\n[第 2 页]\n乙") == [
        (None, "前言"),
        (1, "甲"),
        (2, "乙"),
    ]


def test_build_documents_skips_toc_and_preface():
    documents = build_parent_child_documents(
        text=(
            "[第 1 页]\n工业设备 RAG 知识库文本资料汇编\n封面内容\n"
            "[第 2 页]\n目 录\n前言......\n1 设备概述......\n"
            "[第 3 页]\n前言：用途与入库建议\n使用建议：单块不超过 500 字\n"
            "[第 4 页]\n1 设备概述\n介质温度 0~80℃，允许固体颗粒直径≤10mm。"
        ),
        source="手册.pdf",
        doc_id="doc-noise",
        create_time="2026-11-04 12:00:00",
    )

    assert documents
    assert all("介质温度" in document.page_content for document in documents)
    assert all("目 录" not in document.page_content for document in documents)
    assert all("使用建议" not in document.page_content for document in documents)


def test_noise_filter_keeps_section_when_marker_appears_midbody():
    """正文里出现“使用建议”不能导致整节维护内容被丢掉。"""
    documents = build_parent_child_documents(
        text=(
            "[第 1 页]\n1 日常维护\n"
            "每 500 小时更换轴承润滑油。\n"
            "使用建议：高温环境下缩短到 300 小时。"
        ),
        source="手册.pdf",
        doc_id="doc-keep",
        create_time="2026-11-04 12:00:00",
    )

    assert documents
    assert any("轴承润滑油" in document.page_content for document in documents)


def test_build_parent_child_documents_sets_parent_metadata():
    documents = build_parent_child_documents(
        text="[第 3 页]\n1 设备概述\n" + "甲" * 900,
        source="手册.pdf",
        doc_id="doc-1",
        create_time="2026-11-04 12:00:00",
    )

    assert documents
    assert all(document.metadata["page"] == 3 for document in documents)
    assert all(document.metadata["section"] == "1 设备概述" for document in documents)
    assert all("parent_id" in document.metadata for document in documents)
    assert all("parent_text" in document.metadata for document in documents)
    assert all("1 设备概述" in document.page_content for document in documents)


def test_table_children_repeat_header():
    rows = "\n".join(f"参数{i} | 值{i}" for i in range(80))
    documents = build_parent_child_documents(
        text="[第 1 页]\n1 参数\n参数 | 数值\n" + rows,
        source="表格.pdf",
        doc_id="doc-table",
        create_time="2026-11-04 12:00:00",
    )

    table_children = [
        document for document in documents if "|" in document.page_content
    ]

    assert len(table_children) > 1
    assert all("参数 | 数值" in document.page_content for document in table_children)


def test_expand_parent_documents_deduplicates_children():
    child_a = Document(
        page_content="子块 A",
        metadata={"parent_id": "p1", "parent_text": "父块内容", "source": "手册.pdf"},
    )
    child_b = Document(
        page_content="子块 B",
        metadata={"parent_id": "p1", "parent_text": "父块内容", "source": "手册.pdf"},
    )

    expanded = expand_parent_documents([child_a, child_b])

    assert len(expanded) == 1
    assert expanded[0].page_content == "父块内容"
    assert expanded[0].metadata["parent_id"] == "p1"
    assert "parent_text" not in expanded[0].metadata


def test_expand_parent_pairs_keeps_first_score():
    child = Document(
        page_content="子块",
        metadata={"parent_id": "p1", "parent_text": "父块内容"},
    )

    expanded = expand_parent_pairs([(child, 0.9), (child, 0.5)])

    assert len(expanded) == 1
    assert expanded[0][0].page_content == "父块内容"
    assert expanded[0][1] == 0.9


def test_document_without_parent_metadata_is_kept():
    document = Document(page_content="普通片段", metadata={"source": "a.pdf"})

    assert expand_parent_documents([document]) == [document]
