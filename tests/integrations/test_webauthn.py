import pytest
from integrations import status as status_module


def test_webauthn_stub_success():
    res = status_module._webauthn_check()
    assert "py_webauthn" in res
    assert "registered passkey" in res


def test_webauthn_stub_failure_fallback(monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(status_module, "ROOT", Path("non_existent_folder_abc"))
    # Even if folder doesn't exist, it falls back to 0 registered passkeys
    res = status_module._webauthn_check()
    assert "0 registered passkey" in res


def test_webauthn_live_smoke():
    res = status_module._webauthn_check()
    assert "py_webauthn" in res
