"""知识库上传页面。"""

from __future__ import annotations

import streamlit as st

import config_data as config
from file_parsers import extract_text_from_upload
from knowledge_base import KnowledgeBaseService
from ui_theme import render_file_card, render_page_header


@st.cache_resource
def _get_knowledge_base_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


def render() -> None:
    render_page_header(
        kicker="工业设备 / 知识接入",
        title="知识矩阵",
        accent="上传终端",
        description="解析设备手册、巡检规范和故障案例，将非结构化资料写入可检索的向量知识库。",
        metrics=[
            ("接入格式", "TXT / PDF / DOCX"),
            ("单文件上限", f"{config.max_upload_size_mb} MB"),
            ("写入位置", "本地知识库"),
        ],
        status="接入通道就绪",
    )

    with st.container(key="upload_zone"):
        uploaded_file = st.file_uploader(
            "选择要加入知识库的文件",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=False,
        )

    if uploaded_file is None:
        st.info(
            "上传后会依次执行文本抽取、内容去重和向量写入。",
            icon=":material/sensors:",
        )
        return

    file_size_mb = uploaded_file.size / (1024 * 1024)
    file_format = uploaded_file.name.rsplit(".", maxsplit=1)[-1].upper()
    render_file_card(
        uploaded_file.name,
        file_format,
        file_size_mb,
    )

    if uploaded_file.size > config.max_upload_size_mb * 1024 * 1024:
        st.error(f"文件过大，请上传不超过 {config.max_upload_size_mb} MB 的文件。")
        return

    if not st.button(
        "加入知识库",
        icon=":material/library_add:",
        key="ingest_file",
        type="primary",
    ):
        return

    try:
        service = _get_knowledge_base_service()
    except Exception as exc:
        st.error(f"知识库服务初始化失败：{exc}")
        return

    try:
        with st.spinner("正在解析并写入知识库..."):
            text = extract_text_from_upload(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            result = service.upload_by_str(text, uploaded_file.name)
        st.success(result)
    except Exception as exc:
        st.error(f"知识库更新失败：{exc}")


if __name__ == "__main__":
    render()
