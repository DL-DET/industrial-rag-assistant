"""Streamlit 应用入口。"""

import streamlit as st

from app_file_upload import render as render_upload_page
from app_qa import render as render_qa_page
from ui_theme import apply_global_styles, render_sidebar_brand


st.set_page_config(
    page_title="工业设备智能客服",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_styles()
render_sidebar_brand()

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
