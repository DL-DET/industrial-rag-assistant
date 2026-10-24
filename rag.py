"""RAG 问答服务。"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

import config_data as config
from file_history_store import get_history
from vector_stores import VectorStoreService


def format_documents(documents: Iterable[Document]) -> str:
    """把检索结果整理为带来源信息的上下文。"""
    formatted_documents: list[str] = []
    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "未知来源")
        page = document.metadata.get("page")
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
        return self.retriever.invoke(question)

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
                "history": history.messages,
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
                "history": history.messages,
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
