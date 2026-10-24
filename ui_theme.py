"""工业赛博控制台视觉层。"""

from __future__ import annotations

import html
from collections.abc import Sequence

import streamlit as st


_GLOBAL_STYLES = """
<style>
:root {
    --indus-bg: #070c11;
    --indus-bg-raised: #0a1118;
    --indus-panel: rgba(10, 22, 31, 0.88);
    --indus-panel-solid: #0b151e;
    --indus-line: #173540;
    --indus-line-bright: #2c7182;
    --indus-cyan: #4de8f3;
    --indus-cyan-soft: rgba(77, 232, 243, 0.12);
    --indus-mint: #61f2c2;
    --indus-amber: #ffb454;
    --indus-red: #ff6b7a;
    --indus-text: #ddf2f5;
    --indus-muted: #7e9aa4;
    --indus-display: "Bahnschrift", "DIN Alternate", "Microsoft YaHei", sans-serif;
    --indus-mono: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
}

html, body, .stApp {
    font-family: var(--indus-display);
}

/* 防止中文与等宽字体覆盖 Streamlit 的 Material Symbols 图标字体。 */
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded" !important;
    font-style: normal !important;
    font-weight: normal !important;
    letter-spacing: normal !important;
    line-height: 1 !important;
    text-transform: none !important;
    white-space: nowrap;
}

body {
    background: var(--indus-bg);
}

.stApp {
    color: var(--indus-text);
    background:
        linear-gradient(rgba(77, 232, 243, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(77, 232, 243, 0.025) 1px, transparent 1px),
        linear-gradient(145deg, #070c11 0%, #08121a 45%, #05090d 100%);
    background-size: 48px 48px, 48px 48px, 100% 100%;
}

.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9998;
    opacity: 0.16;
    background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0, 0, 0, 0.34) 3px,
        rgba(0, 0, 0, 0.34) 4px
    );
}

.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    box-shadow: inset 0 0 130px rgba(0, 0, 0, 0.56);
}

header[data-testid="stHeader"] {
    background: rgba(5, 10, 14, 0.72);
    border-bottom: 1px solid rgba(44, 113, 130, 0.34);
    backdrop-filter: blur(18px);
}

[data-testid="stToolbar"] {
    right: 1.2rem;
}

[data-testid="stMainBlockContainer"] {
    width: 100%;
    max-width: 1180px;
    padding-top: 4rem;
    padding-bottom: 7rem;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(rgba(77, 232, 243, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(77, 232, 243, 0.03) 1px, transparent 1px),
        #05090d;
    background-size: 24px 24px;
    border-right: 1px solid var(--indus-line);
    box-shadow: 18px 0 50px rgba(0, 0, 0, 0.2);
}

[data-testid="stSidebarContent"] {
    padding-top: 0.6rem;
}

[data-testid="stSidebarNav"] {
    padding-top: 0.7rem;
}

[data-testid="stSidebarNavLink"] {
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: 2px;
    color: var(--indus-muted);
    font-family: var(--indus-mono);
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    transition: color 160ms ease, background 160ms ease, border-color 160ms ease, transform 160ms ease;
}

[data-testid="stSidebarNavLink"]:hover {
    color: var(--indus-text);
    border-color: rgba(77, 232, 243, 0.26);
    background: rgba(77, 232, 243, 0.06);
    transform: translateX(2px);
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
    color: var(--indus-cyan);
    border-color: rgba(77, 232, 243, 0.34);
    background: linear-gradient(90deg, rgba(77, 232, 243, 0.15), rgba(77, 232, 243, 0.02));
    box-shadow: inset 2px 0 0 var(--indus-cyan);
}

.indus-brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 1.1rem 0.75rem 0.8rem;
    border-bottom: 1px solid var(--indus-line);
}

.indus-brand-mark {
    position: relative;
    display: grid;
    width: 42px;
    height: 42px;
    place-items: center;
    border: 1px solid var(--indus-cyan);
    color: var(--indus-cyan);
    font-family: var(--indus-mono);
    font-size: 0.72rem;
    font-weight: 700;
    clip-path: polygon(0 0, 76% 0, 100% 24%, 100% 100%, 24% 100%, 0 76%);
    box-shadow: inset 0 0 16px rgba(77, 232, 243, 0.12);
}

.indus-brand-mark::after {
    content: "";
    position: absolute;
    right: 4px;
    bottom: 4px;
    width: 5px;
    height: 5px;
    background: var(--indus-mint);
    box-shadow: 0 0 9px var(--indus-mint);
}

.indus-brand-name {
    color: var(--indus-text);
    font-family: var(--indus-mono);
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.09em;
}

.indus-brand-sub {
    margin-top: 0.2rem;
    color: var(--indus-muted);
    font-family: var(--indus-mono);
    font-size: 0.59rem;
    letter-spacing: 0.12em;
}

.indus-side-status {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0.75rem 0.75rem 0.1rem;
    padding: 0.55rem 0.65rem;
    border: 1px solid rgba(97, 242, 194, 0.2);
    background: rgba(97, 242, 194, 0.035);
    color: var(--indus-muted);
    font-family: var(--indus-mono);
    font-size: 0.61rem;
    letter-spacing: 0.08em;
}

.indus-side-status strong {
    color: var(--indus-mint);
    font-weight: 500;
}

.indus-side-status strong::before {
    content: "";
    display: inline-block;
    width: 5px;
    height: 5px;
    margin-right: 0.42rem;
    border-radius: 50%;
    background: var(--indus-mint);
    box-shadow: 0 0 8px var(--indus-mint);
    animation: indus-pulse 2.2s ease-in-out infinite;
}

.cyber-hero {
    position: relative;
    overflow: hidden;
    margin: 0.25rem 0 1.75rem;
    padding: 1.65rem 2rem 1.35rem;
    border: 1px solid var(--indus-line-bright);
    background:
        linear-gradient(120deg, rgba(77, 232, 243, 0.085), transparent 35%),
        linear-gradient(180deg, rgba(12, 25, 35, 0.95), rgba(7, 14, 20, 0.92));
    clip-path: polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 24px 100%, 0 calc(100% - 24px));
    box-shadow: inset 0 0 45px rgba(77, 232, 243, 0.025), 0 18px 55px rgba(0, 0, 0, 0.22);
    animation: indus-boot 520ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.cyber-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
        linear-gradient(90deg, var(--indus-cyan) 0 46px, transparent 46px) top left / 100% 1px no-repeat,
        linear-gradient(180deg, var(--indus-cyan) 0 46px, transparent 46px) top left / 1px 100% no-repeat,
        linear-gradient(270deg, var(--indus-amber) 0 32px, transparent 32px) bottom right / 100% 1px no-repeat,
        linear-gradient(0deg, var(--indus-amber) 0 32px, transparent 32px) bottom right / 1px 100% no-repeat;
    opacity: 0.8;
}

.cyber-hero::after {
    content: "";
    position: absolute;
    top: -60%;
    left: -25%;
    width: 42%;
    height: 220%;
    pointer-events: none;
    background: linear-gradient(90deg, transparent, rgba(77, 232, 243, 0.055), transparent);
    transform: rotate(18deg);
    animation: indus-scan 8s linear infinite;
}

.hero-topline {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.25rem;
}

.hero-kicker {
    color: var(--indus-cyan);
    font-family: var(--indus-mono);
    font-size: 0.64rem;
    letter-spacing: 0.15em;
}

.hero-status {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.28rem 0.58rem;
    border: 1px solid rgba(97, 242, 194, 0.28);
    color: var(--indus-mint);
    background: rgba(97, 242, 194, 0.04);
    font-family: var(--indus-mono);
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    white-space: nowrap;
}

.hero-status::before {
    content: "";
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--indus-mint);
    box-shadow: 0 0 8px var(--indus-mint);
    animation: indus-pulse 2.2s ease-in-out infinite;
}

.hero-title {
    position: relative;
    z-index: 1;
    margin: 0;
    color: var(--indus-text);
    font-family: var(--indus-display);
    font-size: 46px;
    font-weight: 600;
    line-height: 1.05;
    letter-spacing: 0;
}

.hero-title span {
    display: block;
    margin-top: 0.35rem;
    color: var(--indus-cyan);
    text-shadow: 0 0 26px rgba(77, 232, 243, 0.22);
}

.hero-description {
    position: relative;
    z-index: 1;
    max-width: 760px;
    margin: 1rem 0 1.35rem;
    color: #9eb8c0;
    font-size: 0.95rem;
    line-height: 1.75;
}

.hero-metrics {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-top: 1px solid var(--indus-line);
}

.hero-metric {
    min-width: 0;
    padding: 0.85rem 1rem 0.1rem 0;
}

.hero-metric + .hero-metric {
    padding-left: 1rem;
    border-left: 1px solid var(--indus-line);
}

.hero-metric-label {
    color: var(--indus-muted);
    font-family: var(--indus-mono);
    font-size: 0.58rem;
    letter-spacing: 0.1em;
}

.hero-metric-value {
    overflow: hidden;
    margin-top: 0.3rem;
    color: var(--indus-text);
    font-family: var(--indus-mono);
    font-size: 0.77rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

[data-testid="stChatMessage"] {
    position: relative;
    margin-bottom: 0.75rem;
    padding: 1rem 1.1rem;
    border: 1px solid rgba(38, 87, 101, 0.7);
    border-radius: 2px;
    background: linear-gradient(135deg, rgba(12, 23, 32, 0.93), rgba(8, 16, 23, 0.9));
    box-shadow: inset 0 0 28px rgba(77, 232, 243, 0.015);
    backdrop-filter: blur(10px);
}

[data-testid="stChatMessageAvatarCustom"] {
    border: 1px solid rgba(77, 232, 243, 0.44);
    background: rgba(77, 232, 243, 0.1);
    color: var(--indus-cyan);
    box-shadow: inset 0 0 14px rgba(77, 232, 243, 0.08);
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarCustom"]) {
    padding-left: 1.1rem;
}

[data-testid="stChatMessage"]::before {
    content: "";
    position: absolute;
    top: 13px;
    left: -1px;
    width: 2px;
    height: 34px;
    background: var(--indus-cyan);
    box-shadow: 0 0 12px rgba(77, 232, 243, 0.55);
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])::before {
    background: var(--indus-amber);
    box-shadow: 0 0 12px rgba(255, 180, 84, 0.42);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    color: var(--indus-text);
    line-height: 1.72;
}

[data-testid="stBottom"] {
    background: linear-gradient(to top, var(--indus-bg) 54%, rgba(7, 12, 17, 0));
}

[data-testid="stChatInput"] {
    border: 1px solid var(--indus-line-bright);
    border-radius: 2px;
    background: rgba(6, 13, 19, 0.96);
    box-shadow: 0 0 0 1px rgba(77, 232, 243, 0.04), 0 16px 45px rgba(0, 0, 0, 0.34);
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--indus-cyan);
    box-shadow: 0 0 0 1px rgba(77, 232, 243, 0.26), 0 0 28px rgba(77, 232, 243, 0.09);
}

[data-testid="stChatInput"] textarea {
    color: var(--indus-text);
    font-family: var(--indus-display);
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64808a;
}

.stButton button,
.stDownloadButton button {
    min-height: 42px;
    border: 1px solid var(--indus-line-bright);
    border-radius: 2px;
    background: rgba(9, 20, 28, 0.82);
    color: var(--indus-cyan);
    font-family: var(--indus-mono);
    font-size: 0.72rem;
    letter-spacing: 0.07em;
    transition: border-color 160ms ease, background 160ms ease, color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.stButton button:hover,
.stDownloadButton button:hover {
    border-color: var(--indus-cyan);
    background: var(--indus-cyan-soft);
    color: #d9fdff;
    box-shadow: 0 0 22px rgba(77, 232, 243, 0.11);
    transform: translateY(-1px);
}

.st-key-ingest_file button {
    border-color: var(--indus-cyan);
    background: var(--indus-cyan);
    color: #031013;
    font-weight: 700;
}

.st-key-ingest_file button:hover {
    border-color: #9ff9ff;
    background: #9ff9ff;
    color: #031013;
}

.st-key-clear_chat button {
    color: #ffc4cb;
    border-color: rgba(255, 107, 122, 0.38);
    background: rgba(255, 107, 122, 0.035);
}

.st-key-clear_chat button:hover {
    color: #ffffff;
    border-color: var(--indus-red);
    background: rgba(255, 107, 122, 0.12);
    box-shadow: 0 0 20px rgba(255, 107, 122, 0.1);
}

[data-testid="stFileUploaderDropzone"] {
    min-height: 185px;
    border: 1px dashed rgba(77, 232, 243, 0.48);
    border-radius: 2px;
    background:
        linear-gradient(rgba(77, 232, 243, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(77, 232, 243, 0.025) 1px, transparent 1px),
        rgba(8, 18, 25, 0.76);
    background-size: 20px 20px;
    transition: border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--indus-cyan);
    background-color: rgba(77, 232, 243, 0.035);
    box-shadow: inset 0 0 32px rgba(77, 232, 243, 0.035);
}

[data-testid="stFileUploaderDropzone"] button {
    border-color: var(--indus-line-bright);
    background: rgba(77, 232, 243, 0.06);
    color: var(--indus-cyan);
}

[data-testid="stExpander"] {
    border: 1px solid var(--indus-line);
    border-radius: 2px;
    background: rgba(8, 17, 24, 0.74);
}

[data-testid="stExpander"] summary {
    color: #a9c7ce;
    font-family: var(--indus-mono);
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

[data-testid="stAlert"] {
    border: 1px solid var(--indus-line-bright);
    border-radius: 2px;
    background: rgba(11, 24, 33, 0.92);
}

[data-testid="stSpinner"] {
    color: var(--indus-cyan);
}

[data-testid="stCaptionContainer"] {
    color: var(--indus-muted);
}

.indus-file-card {
    position: relative;
    margin: 0.6rem 0 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid var(--indus-line);
    background: rgba(9, 19, 27, 0.82);
    clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
}

.indus-file-card::before {
    content: "文件信息";
    display: block;
    margin-bottom: 0.65rem;
    color: var(--indus-amber);
    font-family: var(--indus-mono);
    font-size: 0.58rem;
    letter-spacing: 0.12em;
}

.indus-file-name {
    overflow-wrap: anywhere;
    color: var(--indus-text);
    font-size: 1rem;
    font-weight: 600;
}

.indus-file-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem 1.25rem;
    margin-top: 0.55rem;
    color: var(--indus-muted);
    font-family: var(--indus-mono);
    font-size: 0.66rem;
}

code, pre, kbd {
    font-family: var(--indus-mono) !important;
}

a {
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
    text-underline-offset: 3px;
}

button:focus-visible,
textarea:focus-visible,
a:focus-visible,
[role="button"]:focus-visible {
    outline: 2px solid var(--indus-cyan) !important;
    outline-offset: 3px !important;
}

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #05090d;
}

::-webkit-scrollbar-thumb {
    border: 2px solid #05090d;
    background: #24525f;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--indus-line-bright);
}

@keyframes indus-boot {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes indus-pulse {
    0%, 100% {
        opacity: 0.55;
    }
    50% {
        opacity: 1;
    }
}

@keyframes indus-scan {
    from {
        transform: translateX(-30%) rotate(18deg);
    }
    to {
        transform: translateX(360%) rotate(18deg);
    }
}

@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"] {
        padding-top: 4.25rem;
    }

    .cyber-hero {
        padding: 1.2rem 1.15rem 1.05rem;
    }

    .hero-topline {
        align-items: flex-start;
        flex-direction: column;
        gap: 0.65rem;
    }

    .hero-title {
        font-size: 34px;
    }

    .hero-description {
        font-size: 0.9rem;
    }

    .hero-metrics {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .hero-metric {
        padding: 0.7rem 0.5rem 0 0;
    }

    .hero-metric + .hero-metric {
        padding-left: 0.5rem;
        border-top: 0;
        border-left: 1px solid var(--indus-line);
    }

    .hero-metric-label {
        font-size: 0.5rem;
        letter-spacing: 0.04em;
        line-height: 1.45;
    }

    .hero-metric-value {
        font-size: 0.62rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        scroll-behavior: auto !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
"""


def apply_global_styles() -> None:
    """每次脚本运行时注入全局样式，Streamlit 重跑后仍会生效。"""
    st.html(_GLOBAL_STYLES)


def render_sidebar_brand() -> None:
    with st.sidebar:
        st.html(
            """
            <div class="indus-brand">
                <div class="indus-brand-mark">智核</div>
                <div>
                    <div class="indus-brand-name">工业智核</div>
                    <div class="indus-brand-sub">设备知识中枢</div>
                </div>
            </div>
            <div class="indus-side-status">
                <span>知识链路</span>
                <strong>在线</strong>
            </div>
            """
        )


def render_page_header(
    *,
    kicker: str,
    title: str,
    accent: str,
    description: str,
    metrics: Sequence[tuple[str, str]],
    status: str = "系统在线",
) -> None:
    metrics_html = "".join(
        (
            '<div class="hero-metric">'
            f'<div class="hero-metric-label">{html.escape(label)}</div>'
            f'<div class="hero-metric-value">{html.escape(value)}</div>'
            "</div>"
        )
        for label, value in metrics
    )
    st.html(
        f"""
        <section class="cyber-hero">
            <div class="hero-topline">
                <div class="hero-kicker">{html.escape(kicker)}</div>
                <div class="hero-status">{html.escape(status)}</div>
            </div>
            <h1 class="hero-title">
                {html.escape(title)}
                <span>{html.escape(accent)}</span>
            </h1>
            <p class="hero-description">{html.escape(description)}</p>
            <div class="hero-metrics">{metrics_html}</div>
        </section>
        """
    )


def render_file_card(filename: str, file_type: str, size_mb: float) -> None:
    st.html(
        f"""
        <section class="indus-file-card">
            <div class="indus-file-name">{html.escape(filename)}</div>
            <div class="indus-file-meta">
                <span>格式 / {html.escape(file_type or '未知')}</span>
                <span>大小 / {size_mb:.2f} MB</span>
                <span>状态 / 待写入</span>
            </div>
        </section>
        """
    )
