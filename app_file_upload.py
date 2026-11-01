"""知识库上传页面。"""

from __future__ import annotations

import streamlit as st

import config_data as config
from file_parsers import extract_text_from_upload
from knowledge_base import KnowledgeBaseService
from ui_theme import (
    render_file_card,
    render_notice,
    render_page_header,
    render_step_bar,
)


STEPS = [
    ("01", "选择文件"),
    ("02", "内容解析"),
    ("03", "写入索引"),
]


@st.cache_resource
def _get_knowledge_base_service() -> KnowledgeBaseService:
    return KnowledgeBaseService()


def render() -> None:
    readiness = config.runtime_readiness()
    render_page_header(
        kicker="工业设备 / 知识接入",
        title="知识矩阵",
        accent="上传终端",
        description="解析设备手册、巡检规范和故障案例，将非结构化资料写入可检索的向量知识库。",
        metrics=[
            ("接入格式 / FORMAT", "TXT / PDF / DOCX"),
            ("单文件上限 / LIMIT", f"{config.max_upload_size_mb} MB"),
            ("写入位置 / STORE", "本地向量库"),
        ],
        status="接入通道就绪" if readiness["api_key"] else "缺少模型密钥",
        doc_no="IQ-KB-07",
    )

    step_slot = st.empty()

    with st.container(key="upload_zone"):
        st.html(
            '<div class="bp-upload-hint">'
            "<span>设备资料 / ENGINEERING DOC</span>"
            "<span>拖拽文件至下方图纸区域</span>"
            "</div>"
        )
        uploaded_file = st.file_uploader(
            "选择要加入知识库的文件",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=False,
        )

    if uploaded_file is None:
        render_step_bar(STEPS, 1, placeholder=step_slot)
        render_notice(
            "上传后会依次执行文本抽取、内容去重和向量写入。",
            "info",
        )
        return

    render_step_bar(STEPS, 2, placeholder=step_slot)

    file_size_mb = uploaded_file.size / (1024 * 1024)
    file_format = uploaded_file.name.rsplit(".", maxsplit=1)[-1].upper()
    file_slot = st.empty()
    render_file_card(
        uploaded_file.name,
        file_format,
        file_size_mb,
        "待写入",
        placeholder=file_slot,
    )

    if uploaded_file.size > config.max_upload_size_mb * 1024 * 1024:
        render_notice(
            f"文件过大，请上传不超过 {config.max_upload_size_mb} MB 的文件。",
            "error",
        )
        return

    if not st.button(
        "加入知识库",
        icon=":material/library_add:",
        key="ingest_file",
        type="primary",
    ):
        return

    render_step_bar(STEPS, 3, placeholder=step_slot)

    try:
        service = _get_knowledge_base_service()
    except Exception as exc:
        render_notice(f"知识库服务初始化失败：{exc}", "error")
        return

    try:
        with st.spinner("正在解析并写入知识库..."):
            text = extract_text_from_upload(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            result = service.upload_by_str(text, uploaded_file.name)
        render_step_bar(STEPS, 3, done=True, placeholder=step_slot)
        if result.status == "success":
            file_status = "已写入"
            notice_kind = "success"
        else:
            file_status = "已存在"
            notice_kind = "info"
        render_file_card(
            uploaded_file.name,
            file_format,
            file_size_mb,
            file_status,
            placeholder=file_slot,
        )
        render_notice(result.message, notice_kind)
    except Exception as exc:
        render_notice(f"知识库更新失败：{exc}", "error")


if __name__ == "__main__":
    render()
