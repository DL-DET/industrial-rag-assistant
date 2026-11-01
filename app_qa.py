"""智能问答页面。"""

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st
from langchain_core.documents import Document

import config_data as config
from rag import PAGE_MARKER_PATTERN, RagService, resolve_page_number
from ui_theme import (
    render_message_label,
    render_notice,
    render_page_header,
    render_quick_prompts,
    render_source_cards,
)


WELCOME_MESSAGE = {
    "role": "assistant",
    "content": "你好，我可以根据工业设备知识库回答设备参数、维护和故障排查问题。",
    "sources": [],
}

QUICK_PROMPTS = [
    ("风机振动如何排查？", "离心风机振动异常如何排查？"),
    ("空压机保养周期？", "空压机的保养周期是多少？"),
    ("减速机漏油怎么办？", "减速机漏油应该怎么处理？"),
    ("轴承温度过高原因？", "电机轴承温度过高的常见原因有哪些？"),
]

CHAT_AVATARS = {
    "assistant": ":material/precision_manufacturing:",
    "user": ":material/engineering:",
}


@st.cache_resource
def _get_rag_service() -> RagService:
    """模型和向量库对象在页面重跑之间复用，避免重复初始化。"""
    return RagService()


def _document_sources(documents: list[Document]) -> list[dict[str, Any]]:
    """提取并去重引用信息，附带片段摘录供引证卡展示。"""
    sources: list[dict[str, Any]] = []
    seen: dict[tuple[str, Any], dict[str, Any]] = {}
    for document in documents:
        source = str(document.metadata.get("source", "未知来源"))
        page = resolve_page_number(document)
        excerpt = " ".join(
            PAGE_MARKER_PATTERN.sub("", document.page_content).split()
        )[:120]
        key = (source, page)
        if key in seen:
            if not seen[key]["excerpt"]:
                seen[key]["excerpt"] = excerpt
            continue
        entry = {"source": source, "page": page, "excerpt": excerpt}
        seen[key] = entry
        sources.append(entry)
    return sources


def _render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(
        f"引证资料 / EVIDENCE · {len(sources)} 项",
        icon=":material/description:",
        expanded=False,
    ):
        render_source_cards(sources)


def _queue_prompt(question: str) -> None:
    """快捷提问：写入待处理队列，由下一次渲染统一消费。"""
    st.session_state.pending_prompt = question


def _role_count(messages: list[dict[str, Any]], role: str) -> int:
    return sum(1 for message in messages if message["role"] == role)


def render() -> None:
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = uuid.uuid4().hex
    if "messages" not in st.session_state:
        st.session_state.messages = [WELCOME_MESSAGE.copy()]

    try:
        rag_service = _get_rag_service()
        service_error = None
    except Exception as exc:
        rag_service = None
        service_error = exc

    render_page_header(
        kicker="工业设备 / 现场智能",
        title="工业设备",
        accent="智能诊断中枢",
        description="从设备知识库检索维护依据，生成可追溯的故障排查与运维回答。",
        metrics=[
            ("向量引擎 / ENGINE", "本地知识库"),
            ("检索片段 / TOP-K", f"{config.retrieval_top_k} 条"),
            ("回答模型 / MODEL", config.chat_model_name),
        ],
        status="本地链路就绪" if rag_service is not None else "服务未就绪",
        doc_no="IQ-QA-04",
    )

    if service_error is not None:
        render_notice(f"服务初始化失败：{service_error}", "error")
        st.stop()

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "归档并新建",
            icon=":material/restart_alt:",
            key="clear_chat",
        ):
            try:
                rag_service.clear_history(st.session_state.chat_session_id)
            except Exception as exc:
                render_notice(f"清空历史记录失败：{exc}", "error")
                st.stop()
            st.session_state.messages = [WELCOME_MESSAGE.copy()]
            st.session_state.pop("pending_prompt", None)
            st.rerun()

    # 快捷提问在渲染消息前取出，避免按钮与新一轮问答同时出现一帧。
    pending_prompt = st.session_state.pop("pending_prompt", None)

    st.html(
        f"""
        <div class="bp-session-bar">
            <span>会话档案 / SESSION</span>
            <code>#{st.session_state.chat_session_id[:6].upper()}</code>
            <span class="bp-session-note">对话历史自动留存</span>
        </div>
        """
    )

    question_no = 0
    answer_no = 0
    for message in st.session_state.messages:
        if message["role"] == "user":
            question_no += 1
            label_no = question_no
        else:
            answer_no += 1
            label_no = answer_no
        with st.chat_message(
            message["role"],
            avatar=CHAT_AVATARS.get(message["role"]),
        ):
            render_message_label(message["role"], label_no)
            st.markdown(message["content"])
            _render_sources(message.get("sources", []))

    if len(st.session_state.messages) == 1 and not pending_prompt:
        render_quick_prompts(QUICK_PROMPTS, _queue_prompt)

    prompt = st.chat_input("输入设备参数、维护或故障排查问题")
    if not prompt:
        prompt = pending_prompt
    if not prompt:
        return

    question_no = _role_count(st.session_state.messages, "user") + 1
    user_message = {"role": "user", "content": prompt, "sources": []}
    st.session_state.messages.append(user_message)
    with st.chat_message("user", avatar=CHAT_AVATARS["user"]):
        render_message_label("user", question_no)
        st.markdown(prompt)

    answer_no = _role_count(st.session_state.messages, "assistant") + 1
    try:
        with st.chat_message("assistant", avatar=CHAT_AVATARS["assistant"]):
            render_message_label("assistant", answer_no)
            with st.status(
                ":shimmer[正在检索知识矩阵]",
                type="compact",
                expanded=False,
            ) as status:
                try:
                    documents = rag_service.retrieve(prompt)
                except Exception as exc:
                    status.update(label="检索失败，请检查知识库或模型配置", state="error")
                    raise
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
        render_notice(f"回答生成失败：{exc}", "error")


if __name__ == "__main__":
    render()
