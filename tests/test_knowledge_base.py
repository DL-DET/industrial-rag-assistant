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
        self.ids = []
        self.deleted = []

    def add_texts(self, texts, metadatas=None):
        start = len(self.texts)
        new_ids = [f"id-{start + index}" for index in range(len(texts))]
        self.texts.extend(texts)
        self.metadatas.extend(metadatas or [])
        self.ids.extend(new_ids)
        return new_ids

    def get(self, where=None, include=None):
        where = where or {}
        indices = [
            index
            for index, metadata in enumerate(self.metadatas)
            if all(metadata.get(key) == value for key, value in where.items())
        ]
        return {
            "ids": [self.ids[index] for index in indices],
            "metadatas": [self.metadatas[index] for index in indices],
        }

    def delete(self, ids=None, where=None):
        ids = set(ids or [])
        self.deleted.extend(ids)
        kept_texts, kept_metadatas, kept_ids = [], [], []
        for text, metadata, doc_id in zip(self.texts, self.metadatas, self.ids):
            if doc_id not in ids:
                kept_texts.append(text)
                kept_metadatas.append(metadata)
                kept_ids.append(doc_id)
        self.texts = kept_texts
        self.metadatas = kept_metadatas
        self.ids = kept_ids


def _make_service(chroma):
    service = KnowledgeBaseService.__new__(KnowledgeBaseService)
    service.chroma = chroma
    service.splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
    )
    service.parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
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
    assert all(metadata["version"] == 1 for metadata in chroma.metadatas)
    assert all(metadata["doc_id"] for metadata in chroma.metadatas)


def test_upload_reports_duplicate(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: True)

    result = service.upload_by_str("重复内容", "手册.pdf")

    assert result.status == "skipped"
    assert result.chunks == 0
    assert chroma.texts == []


def test_upload_creates_parent_child_metadata(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)
    monkeypatch.setattr(kb, "save_md5", lambda _: None)

    result = service.upload_by_str(
        "[第 2 页]\n1 设备概述\n" + "甲" * 1200,
        "长文档.pdf",
    )

    assert result.status == "success"
    assert result.chunks > 1
    assert all(metadata["page"] == 2 for metadata in chroma.metadatas)
    assert all("parent_id" in metadata for metadata in chroma.metadatas)
    assert all("parent_text" in metadata for metadata in chroma.metadatas)
    assert all(metadata["section"] == "1 设备概述" for metadata in chroma.metadatas)
    assert len({metadata["parent_id"] for metadata in chroma.metadatas}) >= 1


def test_upload_returns_parent_text_for_child(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)
    monkeypatch.setattr(kb, "save_md5", lambda _: None)

    service.upload_by_str(
        "[第 1 页]\n甲内容\n[第 2 页]\n乙内容",
        "手册.pdf",
    )

    assert chroma.metadatas[0]["parent_text"] == "甲内容"
    assert chroma.metadatas[1]["parent_text"] == "乙内容"


def test_upload_replaces_old_source_with_new_version(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)
    monkeypatch.setattr(kb, "save_md5", lambda _: None)

    service.upload_by_str("第一版内容", "手册.pdf")
    old_ids = list(chroma.ids)
    service.upload_by_str("第二版内容", "手册.pdf")

    assert chroma.deleted == old_ids
    assert all(metadata["version"] == 2 for metadata in chroma.metadatas)
    assert all("第二版" in text for text in chroma.texts)


def test_upload_rolls_back_vectors_when_md5_save_fails(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)

    def fail_save(_):
        raise OSError("disk full")

    monkeypatch.setattr(kb, "save_md5", fail_save)

    try:
        service.upload_by_str("内容", "手册.pdf")
    except OSError:
        pass
    else:
        raise AssertionError("save_md5 失败时应抛出异常")

    assert chroma.texts == []
    assert len(chroma.deleted) == 1


def test_delete_by_source_removes_all_chunks(monkeypatch):
    chroma = FakeChroma()
    service = _make_service(chroma)
    monkeypatch.setattr(kb, "check_md5", lambda _: False)
    monkeypatch.setattr(kb, "save_md5", lambda _: None)
    service.upload_by_str("[第 1 页]\n甲内容", "手册.pdf")

    removed = service.delete_by_source("手册.pdf")

    assert removed >= 1
    assert chroma.texts == []
