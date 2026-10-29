from pathlib import Path

import pytest

from dema.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEMA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DEMA_REDIS_URL", raising=False)


def test_defaults_point_to_local_compose() -> None:
    settings = Settings()

    assert str(settings.database_url) == "postgresql://dema:dema@localhost:5432/dema"
    assert str(settings.redis_url) == "redis://localhost:6379/0"


def test_reads_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMA_REDIS_URL", "redis://cache:6380/2")

    assert str(Settings().redis_url) == "redis://cache:6380/2"


def test_reads_dotenv_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DEMA_REDIS_URL=redis://trench:6379/1\n")

    assert str(Settings().redis_url) == "redis://trench:6379/1"


def test_rejects_invalid_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMA_DATABASE_URL", "mysql://dema@localhost/dema")

    with pytest.raises(ValueError, match="database_url"):
        Settings()
