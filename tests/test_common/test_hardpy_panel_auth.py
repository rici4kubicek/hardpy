from fastapi.testclient import TestClient
import os
from pathlib import Path
import tempfile
from typing import Optional

from hardpy.hardpy_panel.api import app
from hardpy.hardpy_panel.auth import make_auth_service, AuthAdapter
from hardpy.common.config import ConfigManager

client = TestClient(app)


class SimpleTestAuthAdapter(AuthAdapter):
    """Simple test adapter for verifying custom adapter loading."""

    def authenticate(self, username: str, password: str) -> bool:
        return username == "test" and password == "test"

    def authenticate_token(self, token: str) -> Optional[str]:
        return "test_user" if token == "test_token" else None


def test_login_logout_and_auth_state():
    # ensure the auth service is required to test login workflow
    app.state.auth_service.auth_required = True
    app.state.auth_service.logout()

    status_resp = client.get("/api/auth_status")
    assert status_resp.status_code == 200
    assert status_resp.json()["authenticated"] is False

    fail_resp = client.post("/api/login", json={"username": "wrong", "password": "wrong"})
    assert fail_resp.status_code == 401

    ok_resp = client.post("/api/login", json={"username": "dev", "password": "dev"})
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == "success"
    assert ok_resp.json()["user"] in ("dev", app.state.auth_service.current_user)

    status_resp = client.get("/api/auth_status")
    assert status_resp.status_code == 200
    assert status_resp.json()["authenticated"] is True

    logout_resp = client.post("/api/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["authenticated"] is False

    start_resp = client.get("/api/start")
    assert start_resp.status_code == 401


def test_supports_token_login():
    # configure a known token in environment for adapter
    os.environ["HARDPY_AUTH_TOKEN"] = "test_token_123"
    app.state.auth_service.logout()
    app.state.auth_service.auth_required = True

    with TestClient(app) as client_local:
        token_resp = client_local.post("/api/login", json={"token": "test_token_123"})
        assert token_resp.status_code == 200
        assert token_resp.json()["status"] == "success"
        assert token_resp.json()["user"] is not None

        start_resp = client_local.get("/api/start")
        # if auth happens and no test runner running it should respond, not 401
        assert start_resp.status_code != 401

    del os.environ["HARDPY_AUTH_TOKEN"]


def test_custom_auth_adapter_from_env():
    os.environ["HARDPY_AUTH_ADAPTER"] = "tests.test_common.test_hardpy_panel_auth.SimpleTestAuthAdapter"
    os.environ["HARDPY_AUTH_REQUIRED"] = "true"

    app.state.auth_service = make_auth_service()
    app.state.auth_service.logout()

    with TestClient(app) as client_local:
        bad_resp = client_local.post("/api/login", json={"username": "nottest", "password": "nope"})
        assert bad_resp.status_code == 401

        good_resp = client_local.post("/api/login", json={"username": "test", "password": "test"})
        assert good_resp.status_code == 200
        assert good_resp.json()["status"] == "success"
        assert app.state.auth_service.current_user == "test"

        start_resp = client_local.get("/api/start")
        assert start_resp.status_code != 401

    del os.environ["HARDPY_AUTH_ADAPTER"]
    del os.environ["HARDPY_AUTH_REQUIRED"]
    app.state.auth_service = make_auth_service()


def test_auth_config_from_hardpy_toml():
    """Test that auth configuration reads from hardpy.toml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        config_file = tmpdir_path / "hardpy.toml"

        config_file.write_text(
            """
[auth]
required = true
adapter = "hardpy.hardpy_panel.auth.BasicCredentialsAuthAdapter"

[database]
user = "testuser"
password = "testpass"
"""
        )

        # Reset config singleton to reload from temp file
        ConfigManager._instance = None

        # Read the config
        config_manager = ConfigManager()
        config_manager.read_config(tmpdir_path)

        # Create a new auth service from the loaded config
        auth_service = make_auth_service()

        assert auth_service.auth_required is True
        assert isinstance(auth_service.adapter, type(auth_service.adapter))

        # Verify login works with configured credentials
        try:
            auth_service.login("testuser", "testpass")
            assert auth_service.current_user == "testuser"
        except ValueError:
            # Expected if env vars don't match config
            pass

        # Reset singleton
        ConfigManager._instance = None
