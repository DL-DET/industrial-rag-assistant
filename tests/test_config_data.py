import config_data as config


def test_runtime_readiness_reports_key_and_vector_store(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "persist_directory", tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    assert config.runtime_readiness() == {
        "api_key": True,
        "vector_store": True,
    }

    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    assert config.runtime_readiness()["api_key"] is False


def test_runtime_readiness_reports_missing_vector_store(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "persist_directory", tmp_path / "missing")

    assert config.runtime_readiness()["vector_store"] is False
