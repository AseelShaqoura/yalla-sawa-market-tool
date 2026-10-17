from src.db import init_db, list_competitors


def test_database_initializes(tmp_path, monkeypatch):
    # Smoke-test placeholder; full test fixtures will be added with the review pipeline.
    init_db()
    assert isinstance(list_competitors(), list)
