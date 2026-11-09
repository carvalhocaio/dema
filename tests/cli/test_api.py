import pytest
from fastapi import FastAPI

from dema.cli import api, main


def test_serve_runs_uvicorn_with_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, str, int]] = []
    monkeypatch.setattr(
        api.uvicorn, "run", lambda app, host, port: calls.append((app, host, port))
    )

    main(["api", "serve", "--host", "0.0.0.0", "--port", "9000"])

    [(app, host, port)] = calls
    assert isinstance(app, FastAPI)
    assert (host, port) == ("0.0.0.0", 9000)
