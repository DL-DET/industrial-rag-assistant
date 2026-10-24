"""智能问答页面。"""

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st
from langchain_core.documents import Document

import config_data as config
from file_history_store import get_history
from rag import RagService
from ui_theme import render_page_header


WELCOME_MESSAGE = {
    "role": "assistant",
    "content": "你好，我可以根据工业设备知识库回答设备参数、维护和故障排查问题。",
    "sources": [],
}

CHAT_AVATARS = {
    "assistant": ":material/precision_manufacturing:",
    "user": ":material/engineering:",
}

@st.cache_resource
def _get_rag_service() -> RagService:
    """模型和向量库对象在页面重跑之间复用，避免重复初始化。"""
    return RagService()


def _document_sources(documents: list[Document]) -> list[dict[str, Any]]:
    """提取并去重引用信息，供页面展示。"""
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, Any]] = set()
    for document in documents:
        source = document.metadata.get("source", "未知来源")
        page = document.metadata.get("page")
        key = (str(source), page)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source": str(source), "page": page})
    return sources


def _render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(
        f"检索来源 / {len(sources)} 项",
        icon=":material/hub:",
        expanded=False,
    ):
        for source in sources:
            page = source.get("page")
            page_text = f"，第 {page} 页" if page is not None else ""
            st.markdown(f"- {source['source']}{page_text}")


def render() -> None:
    render_page_header(
        kicker="工业设备 / 现场智能",
        title="工业设备",
        accent="智能诊断中枢",
        description="从设备知识库检索维护依据，生成可追溯的故障排查与运维回答。",
        metrics=[
            ("向量引擎", "本地知识库"),
            ("检索片段", f"{config.retrieval_top_k} 条"),
            ("回答模型", "通义千问"),
        ],
        status="智能链路在线",
    )

    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = uuid.uuid4().hex
    if "messages" not in st.session_state:
        st.session_state.messages = [WELCOME_MESSAGE.copy()]

    try:
        rag_service = _get_rag_service()
    except Exception as exc:
        st.error(f"服务初始化失败：{exc}")
        st.stop()

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "重置会话",
            icon=":material/restart_alt:",
            key="clear_chat",
        ):
            try:
                rag_service.clear_history(st.session_state.chat_session_id)
            except Exception as exc:
                st.error(f"清空历史记录失败：{exc}")
                st.stop()
            st.session_state.messages = [WELCOME_MESSAGE.copy()]
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(
            message["role"],
            avatar=CHAT_AVATARS.get(message["role"]),
        ):
            st.markdown(message["content"])
            _render_sources(message.get("sources", []))

    prompt = st.chat_input(
        "输入设备参数、维护或故障排查问题",
        submit_mode="disable",
    )
    if not prompt:
        return

    user_message = {"role": "user", "content": prompt, "sources": []}
    st.session_state.messages.append(user_message)
    with st.chat_message("user", avatar=CHAT_AVATARS["user"]):
        st.markdown(prompt)

    try:
        with st.chat_message("assistant", avatar=CHAT_AVATARS["assistant"]):
            with st.status(
                ":shimmer[正在检索知识矩阵]",
                type="compact",
                expanded=False,
            ) as status:
                documents = rag_service.retrieve(prompt)
                sources = _document_sources(documents)
                st.caption(f"命中 {len(documents)} 个知识片段")
                status.update(
                    label=f"检索完成，命中 {len(documents)} 个片段",
                    state="complete",
                )

            answer_chunks: list[str] = []

            def capture_stream():
                for chunk in rag_service.stream_answer(
                    prompt,
                    st.session_state.chat_session_id,
                    documents,
                ):
                    answer_chunks.append(chunk)
                    yield chunk

            st.write_stream(capture_stream())
            answer = "".join(answer_chunks).strip()
            _render_sources(sources)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer or "本次回答为空，请重试。",
                "sources": sources,
            }
        )
    except Exception as exc:
        st.error(f"回答生成失败：{exc}")


if __name__ == "__main__":
    render()
