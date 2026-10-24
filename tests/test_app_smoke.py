from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_app_renders_without_exceptions():
    app = AppTest.from_file(PROJECT_ROOT / "app.py", default_timeout=30).run()

    assert app.exception == []
    assert len(app.chat_input) == 1


def test_upload_page_renders_without_exceptions():
    app = AppTest.from_file(
        PROJECT_ROOT / "app_file_upload.py",
        default_timeout=30,
    ).run()

    assert app.exception == []
    assert len(app.get("file_uploader")) == 1
