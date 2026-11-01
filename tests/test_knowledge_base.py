from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
import knowledge_base as kb
from knowledge_base import (
    KnowledgeBaseService,
    check_md5,
    get_string_md5,
    save_md5,
    split_text_by_page,
)


class FakeChroma:
    def __init__(self):
        self.texts = []
        self.metadatas = []

    def add_texts(self, texts, metadatas=None):
        self.texts.extend(texts)
        self.metadatas.extend(metadatas or [])


def _make_service(chroma):
    service = KnowledgeBaseService.__new__(KnowledgeBaseService)
    service.chroma = chroma
    service.splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
    )
    return service


def test_md5_helpers_and_deduplication_state(tmp_path, monkeypatch):
    state_path = tmp_path / "md5_text"
    monkeypatch.setattr(config, "md5_path", state_path)

    fingerprint = get_string_md5("工业离心风机")

    assert check_md5(fingerprint) is False
    save_md5(fingerprint)
    assert check_md5(fingerprint) is True


def test_md5_changes_with_content():
    assert get_string_md5("风机 A") != get_string_md5("风机 B")


def test_split_text_by_page_keeps_page_numbers():
    sections = split_text_by_page("前言\n[第 1 页]\n甲\n[第 2 页]\n乙")

    assert sections == [(None, "前言"), (1, "甲"), (2, "乙")]


def test_split_text_without_page_marker():
    assert split_text_by_page("普通文本") == [(None, "普通文本")]


def test_upload_returns_success_with_page_metadata(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)
    monkeypatch.setattr(kb, "save_md5", lambda _: None)

    result = service.upload_by_str(
        "[第 1 页]\n甲内容\n[第 2 页]\n乙内容",
        "手册.pdf",
    )

    assert result.status == "success"
    assert result.chunks == 2
    assert [metadata["page"] for metadata in chroma.metadatas] == [1, 2]
    assert all(metadata["source"] == "手册.pdf" for metadata in chroma.metadatas)


def test_upload_reports_duplicate(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: True)

    result = service.upload_by_str("重复内容", "手册.pdf")

    assert result.status == "skipped"
    assert result.chunks == 0
    assert chroma.texts == []
