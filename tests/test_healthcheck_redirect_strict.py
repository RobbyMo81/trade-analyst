import os
from importlib import reload


def _write_cfg(tmp_path, redirect_actual: str, registered: list[str]) -> None:
    tmp_path.joinpath("config.toml").write_text(f"""
[auth]
registered_uris = {registered}

[env.dev]
redirect_uri = "{redirect_actual}"
""", encoding="utf-8")


def test_healthcheck_redirect_strict_fail(tmp_path, monkeypatch):
    _write_cfg(tmp_path, "https://127.0.0.1:8443/auth/redirect", ["https://127.0.0.1:5000/oauth2/callback"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HC_STRICT_REDIRECT", "true")
    monkeypatch.setenv("AUTH_SIMULATE", "false")
    from app import healthcheck as hc
    reload(hc)
    rc = hc.run_healthcheck("dev")
    assert rc == 2


def test_healthcheck_redirect_relaxed_with_simulation(tmp_path, monkeypatch):
    _write_cfg(tmp_path, "https://127.0.0.1:8443/auth/redirect", ["https://127.0.0.1:5000/oauth2/callback"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HC_STRICT_REDIRECT", "false")
    monkeypatch.setenv("AUTH_SIMULATE", "true")
    from app import healthcheck as hc
    reload(hc)
    rc = hc.run_healthcheck("dev")
    assert rc == 0  # downgraded to warning under simulate+relaxed
