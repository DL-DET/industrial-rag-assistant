"""Streamlit 应用入口。"""

import streamlit as st

import config_data as config
from app_file_upload import render as render_upload_page
from app_qa import render as render_qa_page
from ui_theme import apply_global_styles, render_sidebar_brand


st.set_page_config(
    page_title="工业智核 · 设备知识中枢",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="auto",
)

apply_global_styles()
readiness = config.runtime_readiness()
render_sidebar_brand(
    [
        ("模型密钥", "已配置" if readiness["api_key"] else "缺少密钥"),
        ("向量库", "已建库" if readiness["vector_store"] else "待建库"),
        ("检索片段", f"TOP-{config.retrieval_top_k}"),
        ("回答模型", config.chat_model_name),
    ]
)

navigation = st.navigation(
    [
        st.Page(
            render_qa_page,
            title="智能问答",
            icon=":material/support_agent:",
            url_path="qa",
            default=True,
        ),
        st.Page(
            render_upload_page,
            title="知识库更新",
            icon=":material/database_upload:",
            url_path="knowledge-base",
        ),
    ]
)
navigation.run()
