"""把上传文件转换为纯文本。"""

from __future__ import annotations

from io import BytesIO

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def decode_text_file(data: bytes) -> str:
    """兼容常见中文文本编码，优先使用 UTF-8。"""
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文本编码，请将文件保存为 UTF-8 后重试")


def extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("PDF 已加密，请解除密码后再上传")

    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        # 扫描版 PDF 的 extract_text 通常返回 None，这里显式转换为空字符串。
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append(f"[第 {page_number} 页]\n{page_text}")
    return "\n\n".join(pages)


def extract_docx_text(data: bytes) -> str:
    document = Document(BytesIO(data))
    blocks = [paragraph.text.strip() for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))
    return "\n".join(block for block in blocks if block)


def validate_file_signature(suffix: str, data: bytes) -> None:
    """校验基本文件头，避免仅改扩展名的非目标文件进入解析器。"""
    if not data:
        raise ValueError("文件内容为空")

    if suffix == ".pdf" and b"%PDF-" not in data[:1024]:
        raise ValueError("文件内容不是有效的 PDF（缺少 %PDF 文件头）")

    if suffix == ".docx" and not data.startswith(b"PK"):
        raise ValueError("文件内容不是有效的 DOCX（缺少 ZIP 文件头）")

    if suffix == ".txt" and b"\x00" in data:
        raise ValueError("文件内容包含二进制字符，请上传纯文本文件")


def extract_text_from_upload(filename: str, data: bytes) -> str:
    suffix = "." + filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型：{suffix or '未知'}")

    validate_file_signature(suffix, data)

    if suffix == ".txt":
        text = decode_text_file(data)
    elif suffix == ".pdf":
        text = extract_pdf_text(data)
    else:
        text = extract_docx_text(data)

    text = text.strip()
    if not text:
        raise ValueError(
            "未从文件中提取到文本。若为扫描版 PDF，请先使用 OCR 转换为可搜索 PDF"
        )
    return text
