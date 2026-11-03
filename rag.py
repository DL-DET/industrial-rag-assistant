"""RAG 问答服务。"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Iterator, Sequence

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import config_data as config
from file_history_store import get_history
from rerank import RerankService
from vector_stores import VectorStoreService


logger = logging.getLogger(__name__)

PAGE_MARKER_PATTERN = re.compile(r"\[第\s*(\d+)\s*页\]")


def resolve_page_number(document: Document) -> int | None:
    """优先读取 metadata 页码；旧数据没有 metadata 时回退解析正文页码标记。"""
    page = document.metadata.get("page")
    if page is not None:
        try:
            return int(page)
        except (TypeError, ValueError):
            pass

    match = PAGE_MARKER_PATTERN.search(document.page_content)
    return int(match.group(1)) if match else None


def recent_history(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """只保留最近若干条历史消息，避免多轮对话无限撑大 Prompt。"""
    return list(messages[-config.max_history_messages :])


def format_documents(documents: Iterable[Document]) -> str:
    """把检索结果整理为带来源信息的上下文。"""
    formatted_documents: list[str] = []
    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "未知来源")
        page = resolve_page_number(document)
        page_text = f"，第 {page} 页" if page is not None else ""
        formatted_documents.append(
            f"[资料 {index}] 来源：{source}{page_text}\n{document.page_content}"
        )

    if not formatted_documents:
        return "知识库中没有检索到相关资料。"
    return "\n\n".join(formatted_documents)


class RagService:
    def __init__(self):
        config.ensure_dashscope_api_key()
        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name)
        )
        self.retriever = self.vector_service.get_retriever()
        self.reranker = RerankService() if config.rerank_enabled else None
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是工业设备知识库助手。请优先依据用户提供的参考资料回答，"
                    "回答要简洁、专业，并明确标注引用的文件名。"
                    "如果参考资料不足以回答，请直接说明“知识库中暂无足够依据”，"
                    "不要编造参数、步骤或结论。",
                ),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "参考资料：\n{context}\n\n用户问题：{input}",
                ),
            ]
        )
        self.chat_model = ChatTongyi(
            model=config.chat_model_name,
            streaming=True,
        )
        self.answer_chain = self.prompt_template | self.chat_model | StrOutputParser()

    def retrieve(self, question: str) -> list[Document]:
        """先向量召回候选片段，再按问题相关性重排；重排失败时回退纯向量结果。

        重排是“精排”：向量检索负责尽量不漏（召回），重排负责把最相关
        的片段排到前面（排序）。多召回一些候选、最终只保留 top_n，
        用少量延迟换取更高的 recall@1。
        """
        if self.reranker is None:
            return self.retriever.invoke(question)

        candidates = self.vector_service.search_with_scores(
            question,
            k=config.rerank_candidate_k,
        )
        documents = [document for document, _ in candidates]
        if not documents:
            return []

        try:
            reranked = self.reranker.rerank(
                question,
                documents,
                top_n=config.rerank_top_n,
            )
        except Exception:
            # 外部重排服务可能超时或限流；不能让整个问答因此不可用，
            # 回退到向量检索的前 top_k 条，保证服务可用性。
            logger.exception("重排失败，回退到纯向量检索")
            return documents[: config.retrieval_top_k]

        if not reranked:
            return documents[: config.retrieval_top_k]
        return [document for document, _ in reranked]

    def stream_answer(
        self,
        question: str,
        session_id: str,
        documents: list[Document] | None = None,
    ) -> Iterator[str]:
        """流式生成回答，并在完整返回后保存本轮问答历史。"""
        documents = documents if documents is not None else self.retrieve(question)
        history = get_history(session_id)
        stream = self.answer_chain.stream(
            {
                "input": question,
                "context": format_documents(documents),
                "history": recent_history(history.messages),
            }
        )

        def generate() -> Iterator[str]:
            answer_chunks: list[str] = []
            for chunk in stream:
                answer_chunks.append(chunk)
                yield chunk

            # 流式请求完整结束后再落盘，避免网络中断时把残缺回答写入历史。
            answer = "".join(answer_chunks).strip()
            if answer:
                history.add_messages(
                    [HumanMessage(content=question), AIMessage(content=answer)]
                )

        return generate()

    def invoke_answer(
        self,
        question: str,
        session_id: str,
        documents: list[Document] | None = None,
    ) -> str:
        documents = documents if documents is not None else self.retrieve(question)
        history = get_history(session_id)
        answer = self.answer_chain.invoke(
            {
                "input": question,
                "context": format_documents(documents),
                "history": recent_history(history.messages),
            }
        )
        if answer.strip():
            history.add_messages(
                [HumanMessage(content=question), AIMessage(content=answer)]
            )
        return answer

    def clear_history(self, session_id: str) -> None:
        get_history(session_id).clear()


if __name__ == "__main__":
    service = RagService()
    demo_documents = service.retrieve("工业离心风机如何保养")
    for chunk in service.stream_answer(
        "工业离心风机如何保养",
        session_id="cli_demo",
        documents=demo_documents,
    ):
        print(chunk, end="")
