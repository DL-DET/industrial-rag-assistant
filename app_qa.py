"""智能问答页面。"""

from __future__ import annotations

import time
import uuid
from typing import Any

import streamlit as st
from langchain_core.documents import Document

import config_data as config
from citation import add_citations
from observability import QueryTrace, new_trace_id, write_trace
from rag import (
    PAGE_MARKER_PATTERN,
    REFUSAL_ANSWER,
    RagService,
    resolve_page_number,
    should_refuse,
)
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
            (
                "检索链路 / PIPELINE",
                "向量召回 + 重排" if config.rerank_enabled else "纯向量检索",
            ),
            (
                "候选片段 / CANDIDATES",
                (
                    f"{config.rerank_candidate_k} → {config.rerank_top_n} 条"
                    if config.rerank_enabled
                    else f"TOP-{config.retrieval_top_k}"
                ),
            ),
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
            if message.get("trace_id"):
                st.caption(f"TRACE #{message['trace_id']}")

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
    trace_id = new_trace_id()
    trace = QueryTrace(
        trace_id=trace_id,
        session_id=st.session_state.chat_session_id,
        query_chars=len(prompt),
    )
    generation_started: float | None = None
    answer_chunks: list[str] = []
    try:
        with st.chat_message("assistant", avatar=CHAT_AVATARS["assistant"]):
            render_message_label("assistant", answer_no)
            with st.status(
                ":shimmer[正在检索知识矩阵]",
                type="compact",
                expanded=False,
            ) as status:
                try:
                    documents, trace = rag_service.retrieve_with_trace(
                        prompt,
                        trace_id=trace_id,
                        session_id=st.session_state.chat_session_id,
                    )
                except Exception as exc:
                    trace.error = str(exc)
                    status.update(label="检索失败，请检查知识库或模型配置", state="error")
                    raise
                sources = _document_sources(documents)
                st.caption(f"命中 {len(documents)} 个知识片段")
                if trace.fallback:
                    st.caption("重排不可用，已降级为向量检索")
                refused = should_refuse(trace)
                if refused:
                    status.update(label="依据不足，已跳过生成", state="complete")
                else:
                    status.update(
                        label=(
                            f"重排完成，保留 {len(documents)} 个片段"
                            if trace.rerank_status == "success"
                            else f"检索完成，命中 {len(documents)} 个片段"
                        ),
                        state="complete",
                    )

            if refused:
                # 依据不足：不调用生成模型。既避免编造，也省掉约 6 秒生成耗时。
                trace.refused = True
                trace.refusal_reason = "score_below_threshold"
                answer = REFUSAL_ANSWER
                trace.answer_chars = len(answer)
                rag_service.record_turn(
                    prompt, answer, st.session_state.chat_session_id
                )
                st.markdown(answer)
                st.caption(
                    f"Top-1 分数 {trace.top_score:.2f} 低于阈值 "
                    f"{config.refusal_score_threshold:.2f}，跳过生成"
                )
            else:
                def capture_stream():
                    for chunk in rag_service.stream_answer(
                        prompt,
                        st.session_state.chat_session_id,
                        documents,
                    ):
                        answer_chunks.append(chunk)
                        yield chunk

                generation_started = time.perf_counter()
                stream_slot = st.empty()
                with stream_slot.container():
                    st.write_stream(capture_stream())
                trace.generation_ms = (time.perf_counter() - generation_started) * 1000
                answer = "".join(answer_chunks).strip()
                cited = add_citations(answer, documents)
                if cited != answer:
                    # 流式阶段拿不到完整文本，引用补全只能在生成结束后重绘一次。
                    stream_slot.empty()
                    stream_slot.markdown(cited)
                    answer = cited
                trace.answer_chars = len(answer)
            _render_sources(sources)
            st.caption(f"TRACE #{trace.trace_id}")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer or "本次回答为空，请重试。",
                "sources": sources,
                "trace_id": trace.trace_id,
            }
        )
    except Exception as exc:
        trace.error = trace.error or str(exc)
        render_notice(f"回答生成失败：{exc}", "error")
    finally:
        if generation_started is not None and trace.generation_ms is None:
            trace.generation_ms = (time.perf_counter() - generation_started) * 1000
        # 拒答路径没有流式片段，不能用它覆盖已记录的拒答文案长度。
        if answer_chunks:
            trace.answer_chars = len("".join(answer_chunks))
        write_trace(trace)


if __name__ == "__main__":
    render()
