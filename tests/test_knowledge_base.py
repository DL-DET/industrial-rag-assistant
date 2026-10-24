import config_data as config
from knowledge_base import check_md5, get_string_md5, save_md5


def test_md5_helpers_and_deduplication_state(tmp_path, monkeypatch):
    state_path = tmp_path / "md5_text"
    monkeypatch.setattr(config, "md5_path", state_path)

    fingerprint = get_string_md5("工业离心风机")

    assert check_md5(fingerprint) is False
    save_md5(fingerprint)
    assert check_md5(fingerprint) is True


def test_md5_changes_with_content():
    assert get_string_md5("风机 A") != get_string_md5("风机 B")
