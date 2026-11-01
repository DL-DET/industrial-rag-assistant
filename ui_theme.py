"""蓝图工程档案视觉层。

设计概念：把界面做成一本可交互的设备检修技术档案。
米白绘图纸、墨蓝制图线、安全橙标注、工单编号与印章式状态。
"""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence
from typing import Any

import streamlit as st


_GLOBAL_STYLES = """
<style>
:root {
    --bp-paper: #f3efe4;
    --bp-paper-raised: #fbf8f0;
    --bp-paper-deep: #e9e2d1;
    --bp-ink: #12314f;
    --bp-ink-deep: #0a2237;
    --bp-ink-soft: #3d5a72;
    --bp-muted: #5f6b73;
    --bp-line: rgba(18, 49, 79, 0.22);
    --bp-line-strong: rgba(18, 49, 79, 0.42);
    --bp-grid: rgba(18, 49, 79, 0.055);
    --bp-grid-major: rgba(18, 49, 79, 0.09);
    --bp-accent: #d9551c;
    --bp-accent-deep: #b4470f;
    --bp-accent-dark: #96370a;
    --bp-accent-soft: rgba(217, 85, 28, 0.08);
    --bp-ok: #2f6b4f;
    --bp-ok-soft: rgba(47, 107, 79, 0.08);
    --bp-danger: #b03a2e;
    --bp-danger-soft: rgba(176, 58, 46, 0.07);
    --bp-shadow: rgba(18, 49, 79, 0.10);
    --bp-display: "Bahnschrift", "DIN Alternate", "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
    --bp-mono: "Cascadia Code", "JetBrains Mono", "Consolas", "Noto Sans Mono CJK SC", monospace;
    --bp-body: "Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
}

html, body, .stApp {
    font-family: var(--bp-body);
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
    background: var(--bp-paper);
}

.stApp {
    color: var(--bp-ink);
    background-color: var(--bp-paper);
    background-image:
        linear-gradient(var(--bp-grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--bp-grid) 1px, transparent 1px),
        linear-gradient(var(--bp-grid-major) 1px, transparent 1px),
        linear-gradient(90deg, var(--bp-grid-major) 1px, transparent 1px);
    background-size: 32px 32px, 32px 32px, 160px 160px, 160px 160px;
    background-position: -1px -1px;
}

/* 纸张颗粒：整体压低对比，避免浅色背景发“平”。 */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9998;
    opacity: 0.05;
    mix-blend-mode: multiply;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E");
}

/* 图纸四边的轻微内阴影。 */
.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9997;
    box-shadow: inset 0 0 140px rgba(18, 49, 79, 0.07);
}

header[data-testid="stHeader"] {
    background: rgba(243, 239, 228, 0.88);
    border-bottom: 1px solid var(--bp-line);
    backdrop-filter: blur(12px);
}

[data-testid="stToolbar"] {
    right: 1.2rem;
}

[data-testid="stMainBlockContainer"] {
    width: 100%;
    max-width: 1180px;
    padding-top: 3.6rem;
    padding-bottom: 7.5rem;
}

[data-testid="stSidebar"] {
    background-color: var(--bp-paper-deep);
    background-image:
        linear-gradient(var(--bp-grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--bp-grid) 1px, transparent 1px);
    background-size: 24px 24px;
    border-right: 1.5px solid var(--bp-ink);
    box-shadow: none;
}

[data-testid="stSidebarContent"] {
    padding-top: 0.5rem;
}

[data-testid="stSidebarNav"] {
    padding-top: 0.6rem;
}

[data-testid="stSidebarNavLink"] {
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: 0;
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    transition: color 160ms ease, background 160ms ease, border-color 160ms ease, transform 160ms ease;
}

[data-testid="stSidebarNavLink"]:hover {
    color: var(--bp-ink);
    border-color: var(--bp-line-strong);
    background: var(--bp-paper-raised);
    transform: translateX(2px);
}

[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] *,
[data-testid="stSidebarNavLink"][aria-current="page"] p,
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stMarkdownContainer"] {
    color: var(--bp-paper-raised) !important;
    fill: var(--bp-paper-raised) !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
    color: var(--bp-paper-raised);
    border-color: var(--bp-ink);
    background: var(--bp-ink);
    box-shadow: none;
}

/* ---------- 侧栏图签 ---------- */

.bp-brand {
    margin: 0.7rem 0.75rem 0.25rem;
    border: 1.5px solid var(--bp-ink);
    background: var(--bp-paper-raised);
    box-shadow: 4px 4px 0 var(--bp-shadow);
}

.bp-brand-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.34rem 0.55rem;
    border-bottom: 1px solid var(--bp-line);
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.54rem;
    letter-spacing: 0.13em;
}

.bp-brand-main {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.8rem 0.7rem;
}

.bp-brand-mark {
    display: grid;
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    place-items: center;
    border: 1.5px solid var(--bp-ink);
    background: var(--bp-ink);
    color: var(--bp-paper-raised);
    font-family: var(--bp-mono);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.bp-brand-name {
    color: var(--bp-ink);
    font-size: 0.94rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}

.bp-brand-sub {
    margin-top: 0.2rem;
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.55rem;
    letter-spacing: 0.14em;
}

.bp-spec {
    margin: 0.7rem 0.75rem 0;
    border-top: 1px dashed var(--bp-line-strong);
}

.bp-spec-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.42rem 0.1rem;
    border-bottom: 1px dashed var(--bp-line);
    font-family: var(--bp-mono);
    font-size: 0.6rem;
    letter-spacing: 0.06em;
}

.bp-spec-row span {
    color: var(--bp-muted);
    white-space: nowrap;
}

.bp-spec-row strong {
    overflow: hidden;
    color: var(--bp-ink);
    font-weight: 600;
    text-align: right;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.bp-spec-row strong::before {
    content: "";
    display: inline-block;
    width: 5px;
    height: 5px;
    margin-right: 0.38rem;
    background: var(--bp-line-strong);
    vertical-align: middle;
}

.bp-spec-row.is-online strong {
    color: var(--bp-ok);
}

.bp-spec-row.is-online strong::before {
    background: var(--bp-ok);
    box-shadow: 0 0 6px rgba(47, 107, 79, 0.55);
    animation: bp-pulse 2.2s ease-in-out infinite;
}

.bp-spec-row.is-warning strong {
    color: var(--bp-danger);
}

.bp-spec-row.is-warning strong::before {
    background: var(--bp-danger);
    box-shadow: 0 0 6px rgba(176, 58, 46, 0.45);
}

/* ---------- 页面标题栏（制图标题块） ---------- */

.bp-hero {
    position: relative;
    overflow: hidden;
    margin: 0.25rem 0 1.6rem;
    padding: 1.35rem 1.6rem 1rem;
    border: 1.5px solid var(--bp-ink);
    background: var(--bp-paper-raised);
    box-shadow: 7px 7px 0 var(--bp-shadow);
    animation: bp-rise 420ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.bp-hero::before {
    content: "";
    position: absolute;
    inset: 6px;
    pointer-events: none;
    opacity: 0.5;
    background:
        linear-gradient(var(--bp-ink), var(--bp-ink)) left top / 16px 2px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) left top / 2px 16px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) right top / 16px 2px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) right top / 2px 16px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) left bottom / 16px 2px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) left bottom / 2px 16px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) right bottom / 16px 2px no-repeat,
        linear-gradient(var(--bp-ink), var(--bp-ink)) right bottom / 2px 16px no-repeat;
}

.bp-hero-top {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.05rem;
}

.bp-kicker {
    color: var(--bp-accent-deep);
    font-family: var(--bp-mono);
    font-size: 0.6rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.bp-kicker::before {
    content: "◈ ";
}

.bp-status {
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.26rem 0.55rem;
    border: 1px solid var(--bp-ok);
    background: var(--bp-ok-soft);
    color: var(--bp-ok);
    font-family: var(--bp-mono);
    font-size: 0.58rem;
    letter-spacing: 0.12em;
    white-space: nowrap;
}

.bp-status::before {
    content: "";
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--bp-ok);
    box-shadow: 0 0 6px rgba(47, 107, 79, 0.7);
    animation: bp-pulse 2.2s ease-in-out infinite;
}

.bp-hero-grid {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 186px;
    gap: 1.5rem;
    align-items: start;
}

.bp-hero-title {
    margin: 0;
    color: var(--bp-ink);
    font-family: var(--bp-display);
    font-size: 46px;
    font-weight: 700;
    line-height: 1.04;
    letter-spacing: 0.01em;
}

.bp-hero-title span {
    display: block;
    margin-top: 0.2rem;
    color: var(--bp-accent);
}

.bp-hero-desc {
    max-width: 740px;
    margin: 0.9rem 0 0;
    color: var(--bp-ink-soft);
    font-size: 0.92rem;
    line-height: 1.8;
}

.bp-sheet {
    border: 1px solid var(--bp-line-strong);
    background: var(--bp-paper);
    padding: 0.25rem 0.6rem;
}

.bp-sheet-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.32rem 0;
    border-bottom: 1px dotted var(--bp-line);
    font-family: var(--bp-mono);
    font-size: 0.55rem;
    letter-spacing: 0.08em;
}

.bp-sheet-row:last-child {
    border-bottom: 0;
}

.bp-sheet-row span {
    color: var(--bp-muted);
    white-space: nowrap;
}

.bp-sheet-row strong {
    color: var(--bp-ink);
    font-weight: 600;
    text-align: right;
}

.bp-dim {
    position: relative;
    height: 22px;
    margin-top: 1.15rem;
    border-top: 1px solid var(--bp-line-strong);
}

.bp-dim::before,
.bp-dim::after {
    content: "";
    position: absolute;
    top: -5px;
    width: 1px;
    height: 10px;
    background: var(--bp-line-strong);
}

.bp-dim::before {
    left: 0;
}

.bp-dim::after {
    right: 0;
}

.bp-dim span {
    position: absolute;
    left: 50%;
    top: -0.54rem;
    padding: 0 0.5rem;
    background: var(--bp-paper-raised);
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.52rem;
    letter-spacing: 0.2em;
    transform: translateX(-50%);
    white-space: nowrap;
}

.bp-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.bp-metric {
    min-width: 0;
    padding: 0.65rem 0.9rem 0.1rem 0;
}

.bp-metric + .bp-metric {
    padding-left: 0.9rem;
    border-left: 1px dashed var(--bp-line);
}

.bp-metric-label {
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.54rem;
    letter-spacing: 0.14em;
}

.bp-metric-value {
    overflow: hidden;
    margin-top: 0.3rem;
    color: var(--bp-ink);
    font-family: var(--bp-mono);
    font-size: 0.78rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* ---------- 会话档案条 ---------- */

.bp-session-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0.2rem 0 1rem;
    padding: 0.36rem 0.62rem;
    border: 1px dashed var(--bp-line-strong);
    background: rgba(251, 248, 240, 0.55);
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.56rem;
    letter-spacing: 0.1em;
}

.bp-session-bar code {
    background: none;
    color: var(--bp-ink);
    font-size: 0.62rem;
    padding: 0;
}

.bp-session-note {
    margin-left: auto;
}

/* ---------- 问答消息 ---------- */

[data-testid="stChatMessage"] {
    position: relative;
    margin-bottom: 1.05rem;
    padding: 1.2rem 1.15rem 0.9rem;
    border: 1px solid var(--bp-line-strong);
    border-left: 3px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-paper-raised);
    box-shadow: 4px 4px 0 var(--bp-shadow);
}

[data-testid="stChatMessage"]:has(.bp-msg-label.user) {
    border-left-color: var(--bp-accent);
}

.bp-msg-label {
    position: absolute;
    top: -0.62rem;
    left: 0.95rem;
    z-index: 2;
    padding: 0 0.42rem;
    border: 1px solid var(--bp-line);
    background: var(--bp-paper-raised);
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.55rem;
    letter-spacing: 0.14em;
    line-height: 1.5;
}

.bp-msg-label.user {
    border-color: rgba(217, 85, 28, 0.42);
    color: var(--bp-accent-deep);
}

[data-testid="stChatMessageAvatarCustom"],
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    border: 1.5px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-paper-deep);
    color: var(--bp-ink);
}

[data-testid="stChatMessage"]:has(.bp-msg-label.user) [data-testid="stChatMessageAvatarCustom"],
[data-testid="stChatMessage"]:has(.bp-msg-label.user) [data-testid="stChatMessageAvatarUser"] {
    border-color: var(--bp-accent);
    background: var(--bp-accent-soft);
    color: var(--bp-accent);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    color: var(--bp-ink);
    line-height: 1.78;
}

[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {
    color: var(--bp-ink);
    font-family: var(--bp-display);
}

[data-testid="stChatMessage"] a {
    color: var(--bp-accent-deep);
}

[data-testid="stChatMessage"] code {
    background: var(--bp-paper-deep);
    color: var(--bp-ink-deep);
}

[data-testid="stChatMessage"] blockquote {
    border-left: 2px solid var(--bp-accent);
    color: var(--bp-ink-soft);
}

[data-testid="stChatMessage"] table {
    width: 100%;
    margin: 0.7rem 0;
    border-collapse: collapse;
    font-size: 0.84rem;
}

[data-testid="stChatMessage"] th {
    padding: 0.4rem 0.5rem;
    border-bottom: 1.5px solid var(--bp-ink);
    color: var(--bp-ink);
    font-family: var(--bp-mono);
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-align: left;
}

[data-testid="stChatMessage"] td {
    padding: 0.42rem 0.5rem;
    border-bottom: 1px solid var(--bp-line);
    color: var(--bp-ink);
}

/* ---------- 引证卡片 ---------- */

.bp-sources {
    margin-top: 0.2rem;
}

.bp-sources-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding-bottom: 0.32rem;
    border-bottom: 1px solid var(--bp-ink);
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.56rem;
    letter-spacing: 0.16em;
}

.bp-source {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 0.65rem;
    padding: 0.6rem 0.1rem;
    border-bottom: 1px dashed var(--bp-line);
}

.bp-source:last-child {
    border-bottom: 0;
}

.bp-source-idx {
    display: grid;
    height: 28px;
    place-items: center;
    border: 1px solid rgba(217, 85, 28, 0.4);
    color: var(--bp-accent-deep);
    font-family: var(--bp-mono);
    font-size: 0.66rem;
}

.bp-source-name {
    overflow-wrap: anywhere;
    color: var(--bp-ink);
    font-size: 0.83rem;
    font-weight: 600;
}

.bp-source-meta {
    margin-top: 0.16rem;
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.55rem;
    letter-spacing: 0.1em;
}

.bp-source-excerpt {
    display: -webkit-box;
    overflow: hidden;
    margin: 0.35rem 0 0;
    color: var(--bp-ink-soft);
    font-size: 0.76rem;
    line-height: 1.6;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
}

/* ---------- 快捷提问 ---------- */

.bp-quick-head {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin: 1.25rem 0 0.55rem;
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.58rem;
    letter-spacing: 0.16em;
}

.bp-quick-head::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--bp-line);
}

.st-key-quick_prompts button {
    width: 100%;
    min-height: 44px;
    justify-content: flex-start;
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--bp-line);
    border-radius: 0;
    background: var(--bp-paper-raised);
    box-shadow: none;
    color: var(--bp-ink);
    font-family: var(--bp-body);
    font-size: 0.8rem;
    letter-spacing: 0.01em;
    text-align: left;
}

.st-key-quick_prompts button > div {
    width: 100%;
    justify-content: flex-start;
}

.st-key-quick_prompts button [data-testid="stMarkdownContainer"] {
    width: 100%;
    text-align: left;
}

.st-key-quick_prompts button p {
    font-size: 0.8rem;
    text-align: left;
}

.st-key-quick_prompts button:hover {
    border-color: var(--bp-ink);
    background: var(--bp-paper-deep);
    color: var(--bp-ink);
    box-shadow: none;
    transform: translateX(2px);
}

/* ---------- 聊天输入 ---------- */

[data-testid="stBottom"] {
    background: linear-gradient(to top, var(--bp-paper) 62%, rgba(243, 239, 228, 0));
}

[data-testid="stChatInput"] {
    border: 1.5px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-paper-raised);
    box-shadow: 5px 5px 0 var(--bp-shadow);
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--bp-accent);
    box-shadow: 5px 5px 0 rgba(217, 85, 28, 0.16);
}

[data-testid="stChatInput"] textarea {
    color: var(--bp-ink);
    font-family: var(--bp-body);
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--bp-muted);
}

[data-testid="stChatInput"] button {
    border-radius: 0;
    color: var(--bp-ink);
}

[data-testid="stChatInput"] button:hover {
    background: var(--bp-accent-soft);
    color: var(--bp-accent-deep);
}

/* ---------- 通用按钮 ---------- */

.stButton button,
.stDownloadButton button {
    min-height: 42px;
    border: 1px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-paper-raised);
    box-shadow: 3px 3px 0 var(--bp-shadow);
    color: var(--bp-ink);
    font-family: var(--bp-mono);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    transition: background 160ms ease, color 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.stButton button:hover,
.stDownloadButton button:hover {
    border-color: var(--bp-ink);
    background: var(--bp-ink);
    box-shadow: 4px 4px 0 rgba(18, 49, 79, 0.18);
    color: var(--bp-paper-raised);
    transform: translate(-1px, -1px);
}

.stButton button p,
.stDownloadButton button p,
[data-testid="stFileUploaderDropzone"] button p {
    color: inherit !important;
}

.st-key-ingest_file button {
    border-color: var(--bp-accent-deep);
    background: var(--bp-accent-deep);
    box-shadow: 3px 3px 0 rgba(180, 71, 15, 0.24);
    color: #fff9f0;
    font-weight: 700;
}

.st-key-ingest_file button:hover {
    border-color: var(--bp-accent-dark);
    background: var(--bp-accent-dark);
    box-shadow: 4px 4px 0 rgba(150, 55, 10, 0.28);
    color: #fff9f0;
}

.st-key-clear_chat button {
    border-color: rgba(180, 71, 15, 0.55);
    background: transparent;
    box-shadow: none;
    color: var(--bp-accent-deep);
}

.st-key-clear_chat button:hover {
    border-color: var(--bp-accent-deep);
    background: var(--bp-accent-deep);
    color: #fff9f0;
}

/* ---------- 上传区 ---------- */

[data-testid="stFileUploaderDropzone"] {
    min-height: 190px;
    border: 1.5px dashed var(--bp-line-strong);
    border-radius: 0;
    background-color: var(--bp-paper-raised);
    background-image:
        linear-gradient(var(--bp-grid) 1px, transparent 1px),
        linear-gradient(90deg, var(--bp-grid) 1px, transparent 1px);
    background-size: 20px 20px, 20px 20px;
    transition: border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--bp-accent);
    background-color: var(--bp-accent-soft);
    box-shadow: inset 0 0 32px rgba(217, 85, 28, 0.04);
}

[data-testid="stFileUploaderDropzone"] button {
    border: 1px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-ink);
    color: var(--bp-paper-raised);
}

[data-testid="stFileUploaderDropzone"] button:hover {
    border-color: var(--bp-accent-deep);
    background: var(--bp-accent-deep);
}

[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] * {
    color: var(--bp-ink-soft) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.04em;
}

.bp-upload-hint {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin: 0 0 0.45rem;
    color: var(--bp-ink-soft);
    font-size: 0.8rem;
}

.bp-upload-hint span:first-child {
    color: var(--bp-accent-deep);
    font-family: var(--bp-mono);
    font-size: 0.56rem;
    letter-spacing: 0.16em;
}

.bp-upload-hint span:last-child {
    font-family: var(--bp-mono);
    font-size: 0.58rem;
    letter-spacing: 0.06em;
}

/* ---------- 步骤条 ---------- */

.bp-steps {
    display: flex;
    margin: 0.2rem 0 1.2rem;
    border: 1px solid var(--bp-line-strong);
    background: rgba(251, 248, 240, 0.62);
}

.bp-step {
    display: flex;
    flex: 1;
    align-items: center;
    gap: 0.55rem;
    min-width: 0;
    padding: 0.55rem 0.7rem;
}

.bp-step + .bp-step {
    border-left: 1px dashed var(--bp-line);
}

.bp-step-idx {
    display: grid;
    width: 26px;
    height: 26px;
    flex: 0 0 26px;
    place-items: center;
    border: 1px solid var(--bp-line-strong);
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.6rem;
}

.bp-step-label {
    overflow: hidden;
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.bp-step.is-done .bp-step-idx {
    border-color: var(--bp-ink);
    background: var(--bp-ink);
    color: var(--bp-paper-raised);
}

.bp-step.is-done .bp-step-label {
    color: var(--bp-ink-soft);
}

.bp-step.is-active {
    background: var(--bp-accent-soft);
}

.bp-step.is-active .bp-step-idx {
    border-color: var(--bp-accent-deep);
    color: var(--bp-accent-deep);
}

.bp-step.is-active .bp-step-label {
    color: var(--bp-accent-deep);
    font-weight: 600;
}

/* ---------- 文件图签 ---------- */

.bp-file {
    margin: 0.6rem 0 1rem;
    border: 1.5px solid var(--bp-ink);
    background: var(--bp-paper-raised);
    box-shadow: 5px 5px 0 var(--bp-shadow);
}

.bp-file-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.38rem 0.7rem;
    border-bottom: 1px solid var(--bp-line);
    background: var(--bp-paper-deep);
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.55rem;
    letter-spacing: 0.14em;
}

.bp-file-status {
    color: var(--bp-accent-deep);
}

.bp-file-name {
    overflow-wrap: anywhere;
    padding: 0.72rem 0.8rem 0.3rem;
    color: var(--bp-ink);
    font-size: 1.02rem;
    font-weight: 700;
}

.bp-file-spec {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.5rem;
    margin: 0.2rem 0 0;
    padding: 0.55rem 0.8rem 0.7rem;
    border-top: 1px dashed var(--bp-line);
}

.bp-file-spec dt {
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.54rem;
    letter-spacing: 0.12em;
}

.bp-file-spec dd {
    overflow-wrap: anywhere;
    margin: 0.24rem 0 0;
    color: var(--bp-ink);
    font-family: var(--bp-mono);
    font-size: 0.7rem;
}

/* ---------- 批注 / 提示 ---------- */

.bp-notice {
    margin: 0.6rem 0 1rem;
    padding: 0.68rem 0.85rem;
    border: 1px solid var(--bp-line);
    border-left: 3px solid var(--bp-ink);
    background: var(--bp-paper-raised);
}

.bp-notice-label {
    display: block;
    margin-bottom: 0.28rem;
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.54rem;
    letter-spacing: 0.16em;
}

.bp-notice p {
    margin: 0;
    color: var(--bp-ink);
    font-size: 0.84rem;
    line-height: 1.7;
}

.bp-notice.success {
    border-left-color: var(--bp-ok);
    background: var(--bp-ok-soft);
}

.bp-notice.success .bp-notice-label {
    color: var(--bp-ok);
}

.bp-notice.error {
    border-left-color: var(--bp-danger);
    background: var(--bp-danger-soft);
}

.bp-notice.error .bp-notice-label {
    color: var(--bp-danger);
}

.bp-notice.warning {
    border-left-color: var(--bp-accent);
    background: var(--bp-accent-soft);
}

.bp-notice.warning .bp-notice-label {
    color: var(--bp-accent-deep);
}

/* ---------- 原生组件兜底 ---------- */

[data-testid="stExpander"] {
    border: 1px solid var(--bp-line);
    border-radius: 0;
    background: rgba(251, 248, 240, 0.7);
}

[data-testid="stExpander"] summary {
    color: var(--bp-ink-soft);
    font-family: var(--bp-mono);
    font-size: 0.68rem;
    letter-spacing: 0.06em;
}

[data-testid="stExpander"] summary:hover {
    color: var(--bp-accent-deep);
}

[data-testid="stAlert"] {
    border: 1px solid var(--bp-line-strong);
    border-left: 3px solid var(--bp-ink);
    border-radius: 0;
    background: var(--bp-paper-raised);
    color: var(--bp-ink);
}

[data-testid="stStatusWidget"] {
    border: 1px solid var(--bp-line);
    border-radius: 0;
    background: var(--bp-paper);
    font-family: var(--bp-mono);
    font-size: 0.7rem;
}

[data-testid="stSpinner"] {
    color: var(--bp-accent);
}

[data-testid="stCaptionContainer"] {
    color: var(--bp-muted);
    font-family: var(--bp-mono);
    font-size: 0.62rem;
    letter-spacing: 0.06em;
}

code, pre, kbd {
    font-family: var(--bp-mono) !important;
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
    outline: 2px solid var(--bp-accent) !important;
    outline-offset: 3px !important;
}

::selection {
    background: rgba(217, 85, 28, 0.22);
    color: var(--bp-ink-deep);
}

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bp-paper-deep);
}

::-webkit-scrollbar-thumb {
    border: 2px solid var(--bp-paper-deep);
    background: rgba(18, 49, 79, 0.35);
}

::-webkit-scrollbar-thumb:hover {
    background: var(--bp-ink-soft);
}

@keyframes bp-rise {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes bp-pulse {
    0%, 100% {
        opacity: 0.55;
    }
    50% {
        opacity: 1;
    }
}

@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"] {
        padding-top: 4rem;
    }

    .bp-hero {
        padding: 1.1rem 1.05rem 0.9rem;
    }

    .bp-hero-top {
        align-items: flex-start;
        flex-direction: column;
        gap: 0.6rem;
    }

    .bp-hero-grid {
        grid-template-columns: minmax(0, 1fr);
        gap: 0.9rem;
    }

    .bp-sheet {
        display: flex;
        flex-wrap: wrap;
        gap: 0 1.2rem;
        padding: 0.15rem 0.5rem;
    }

    .bp-sheet-row {
        flex: 1 1 40%;
        border-bottom: 0;
    }

    .bp-hero-title {
        font-size: 34px;
    }

    .bp-hero-desc {
        font-size: 0.88rem;
    }

    .bp-metric {
        padding: 0.6rem 0.45rem 0 0;
    }

    .bp-metric + .bp-metric {
        padding-left: 0.45rem;
    }

    .bp-metric-label {
        font-size: 0.48rem;
        letter-spacing: 0.06em;
        line-height: 1.45;
    }

    .bp-metric-value {
        font-size: 0.62rem;
    }

    .bp-session-note {
        display: none;
    }

    .bp-step {
        gap: 0.4rem;
        padding: 0.5rem 0.45rem;
    }

    .bp-step-label {
        font-size: 0.54rem;
    }

    .bp-file-spec {
        grid-template-columns: repeat(2, minmax(0, 1fr));
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


def render_sidebar_brand(
    specs: Sequence[tuple[str, str]] | None = None,
) -> None:
    """侧栏图签：项目标识 + 运行参数。"""
    specs = specs or [
        ("知识链路", "在线"),
        ("检索策略", "向量检索"),
        ("回答模型", "通义千问"),
    ]
    ok_values = {"在线", "已配置", "已建库", "就绪", "已连接"}
    warn_values = {"缺少密钥", "未配置", "待建库", "未连接"}
    spec_rows: list[str] = []
    for label, value in specs:
        if value in ok_values:
            state_class = " is-online"
        elif value in warn_values:
            state_class = " is-warning"
        else:
            state_class = ""
        spec_rows.append(
            f'<div class="bp-spec-row{state_class}">'
            f"<span>{html.escape(label)}</span>"
            f"<strong>{html.escape(value)}</strong>"
            "</div>"
        )
    spec_html = "".join(spec_rows)
    with st.sidebar:
        st.html(
            f"""
            <div class="bp-brand">
                <div class="bp-brand-top">
                    <span>DWG. NO. IQ-04</span>
                    <span>REV. 03</span>
                </div>
                <div class="bp-brand-main">
                    <div class="bp-brand-mark">智核</div>
                    <div>
                        <div class="bp-brand-name">工业智核</div>
                        <div class="bp-brand-sub">设备知识中枢</div>
                    </div>
                </div>
            </div>
            <div class="bp-spec">{spec_html}</div>
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
    doc_no: str = "IQ-000",
    revision: str = "R03",
) -> None:
    """制图标题栏式页面头部。"""
    metrics_html = "".join(
        (
            '<div class="bp-metric">'
            f'<div class="bp-metric-label">{html.escape(label)}</div>'
            f'<div class="bp-metric-value">{html.escape(value)}</div>'
            "</div>"
        )
        for label, value in metrics
    )
    st.html(
        f"""
        <section class="bp-hero">
            <div class="bp-hero-top">
                <div class="bp-kicker">{html.escape(kicker)}</div>
                <div class="bp-status">{html.escape(status)}</div>
            </div>
            <div class="bp-hero-grid">
                <div class="bp-hero-main">
                    <h1 class="bp-hero-title">
                        {html.escape(title)}
                        <span>{html.escape(accent)}</span>
                    </h1>
                    <p class="bp-hero-desc">{html.escape(description)}</p>
                </div>
                <aside class="bp-sheet">
                    <div class="bp-sheet-row"><span>图号 / DWG</span><strong>{html.escape(doc_no)}</strong></div>
                    <div class="bp-sheet-row"><span>版本 / REV</span><strong>{html.escape(revision)}</strong></div>
                    <div class="bp-sheet-row"><span>比例 / SCALE</span><strong>1:1</strong></div>
                </aside>
            </div>
            <div class="bp-dim"><span>SPECIFICATION</span></div>
            <div class="bp-metrics">{metrics_html}</div>
        </section>
        """
    )


def render_message_label(role: str, number: int) -> None:
    """给消息加上档案编号标签。"""
    is_user = role == "user"
    prefix = "提问单 Q" if is_user else "分析报告 A"
    st.html(
        f'<div class="bp-msg-label{" user" if is_user else ""}">'
        f"{prefix}-{number:02d}"
        "</div>"
    )


def render_source_cards(sources: Sequence[dict[str, Any]]) -> None:
    """引证卡：来源文件、页码与片段摘录。"""
    cards = []
    for index, source in enumerate(sources, start=1):
        page = source.get("page")
        page_text = f"PAGE {page}" if page is not None else "DOCUMENT"
        excerpt = str(source.get("excerpt") or "").strip()
        excerpt_html = (
            f'<p class="bp-source-excerpt">{html.escape(excerpt)}</p>'
            if excerpt
            else ""
        )
        cards.append(
            f"""
            <article class="bp-source">
                <div class="bp-source-idx">{index:02d}</div>
                <div>
                    <div class="bp-source-name">{html.escape(str(source.get("source", "未知来源")))}</div>
                    <div class="bp-source-meta">{page_text} · EVIDENCE</div>
                    {excerpt_html}
                </div>
            </article>
            """
        )
    st.html(
        f"""
        <section class="bp-sources">
            <div class="bp-sources-head">
                <span>引证资料 / EVIDENCE</span>
                <span>{len(sources):02d} 项</span>
            </div>
            {''.join(cards)}
        </section>
        """
    )


def render_quick_prompts(
    prompts: Sequence[tuple[str, str]],
    on_select: Callable[[str], None],
) -> None:
    """欢迎态快捷提问入口。"""
    with st.container(key="quick_prompts"):
        st.html('<div class="bp-quick-head">常用检修入口 / QUICK ENTRY</div>')
        columns = st.columns(2)
        for index, (label, question) in enumerate(prompts):
            columns[index % 2].button(
                label,
                key=f"quick_prompt_{index}",
                icon=":material/north_east:",
                width="stretch",
                on_click=on_select,
                args=(question,),
            )


def render_step_bar(
    steps: Sequence[tuple[str, str]],
    active: int,
    *,
    done: bool = False,
    placeholder: Any = None,
) -> None:
    """上传流程步骤条，active 从 1 开始。"""
    items = []
    for index, (code, label) in enumerate(steps, start=1):
        if done or index < active:
            state = " is-done"
        elif index == active:
            state = " is-active"
        else:
            state = ""
        items.append(
            f'<div class="bp-step{state}">'
            f'<span class="bp-step-idx">{html.escape(code)}</span>'
            f'<span class="bp-step-label">{html.escape(label)}</span>'
            "</div>"
        )
    markup = f'<div class="bp-steps">{"".join(items)}</div>'
    if placeholder is None:
        st.html(markup)
        return
    placeholder.html(markup)


def render_file_card(
    filename: str,
    file_type: str,
    size_mb: float,
    status: str = "待写入",
    *,
    placeholder: Any = None,
) -> None:
    """上传文件的图签式信息卡。"""
    markup = f"""
        <section class="bp-file">
            <div class="bp-file-head">
                <span>附件 / ATTACHMENT</span>
                <span class="bp-file-status">{html.escape(status)}</span>
            </div>
            <div class="bp-file-name">{html.escape(filename)}</div>
            <dl class="bp-file-spec">
                <div><dt>格式 / FORMAT</dt><dd>{html.escape(file_type or '未知')}</dd></div>
                <div><dt>大小 / SIZE</dt><dd>{size_mb:.2f} MB</dd></div>
                <div><dt>状态 / STATE</dt><dd>{html.escape(status)}</dd></div>
            </dl>
        </section>
        """
    if placeholder is None:
        st.html(markup)
        return
    placeholder.html(markup)


_NOTICE_LABELS = {
    "info": "备注 / NOTE",
    "success": "写入完成 / DONE",
    "error": "异常 / FAULT",
    "warning": "注意 / CAUTION",
}


def render_notice(text: str, kind: str = "info") -> None:
    """纸张批注式提示。"""
    kind = kind if kind in _NOTICE_LABELS else "info"
    st.html(
        f"""
        <aside class="bp-notice {kind}">
            <span class="bp-notice-label">{_NOTICE_LABELS[kind]}</span>
            <p>{html.escape(text)}</p>
        </aside>
        """
    )
