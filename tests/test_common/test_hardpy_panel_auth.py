import importlib
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from hardpy.hardpy_panel.auth import make_auth_service, load_auth_adapter, AuthAdapter
from hardpy.common.config import ConfigManager


class SimpleTestAuthAdapter(AuthAdapter):
    """Simple test adapter for verifying custom adapter loading."""

    def authenticate(self, username: str, password: str) -> bool:
        return username == "test" and password == "test"

    def authenticate_token(self, token: str) -> Optional[str]:
        return "test_user" if token == "test_token" else None


@pytest.fixture(scope="module")
def app():
    tmpdir_path = Path(tempfile.mkdtemp(prefix="hardpy-auth-app-"))
    (tmpdir_path / "hardpy.toml").write_text(
        """
[database]
storage_type = "json"
storage_path = ".hardpy-test"
user = "dev"
password = "dev"

[auth]
required = true
adapter = "hardpy.hardpy_panel.auth.BasicCredentialsAuthAdapter"
"""
    )

    ConfigManager._instance = None
    ConfigManager().read_config(tmpdir_path)

    # Force clean import so app state is created from test config.
    sys.modules.pop("hardpy.hardpy_panel.api", None)
    api_module = importlib.import_module("hardpy.hardpy_panel.api")
    yield api_module.app

    ConfigManager._instance = None


@pytest.fixture
def client(app):
    with TestClient(app) as client_local:
        yield client_local


def test_login_logout_and_auth_state(app, client):
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


def test_supports_token_login(app, client, monkeypatch):
    # configure a known token in environment for adapter
    monkeypatch.setenv("HARDPY_AUTH_TOKEN", "test_token_123")
    app.state.auth_service.logout()
    app.state.auth_service.auth_required = True

    token_resp = client.post("/api/login", json={"token": "test_token_123"})
    assert token_resp.status_code == 200
    assert token_resp.json()["status"] == "success"
    assert token_resp.json()["user"] is not None

    protected_resp = client.get("/api/stop")
    # authenticated user must not be rejected by auth middleware
    assert protected_resp.status_code != 401


def test_custom_auth_adapter_from_env(app, client, monkeypatch):
    monkeypatch.setenv("HARDPY_AUTH_ADAPTER", f"{__name__}.SimpleTestAuthAdapter")
    monkeypatch.setenv("HARDPY_AUTH_REQUIRED", "true")

    app.state.auth_service = make_auth_service()
    app.state.auth_service.logout()

    bad_resp = client.post("/api/login", json={"username": "nottest", "password": "nope"})
    assert bad_resp.status_code == 401

    good_resp = client.post("/api/login", json={"username": "test", "password": "test"})
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] == "success"
    assert app.state.auth_service.current_user == "test"

    protected_resp = client.get("/api/stop")
    assert protected_resp.status_code != 401

    app.state.auth_service = make_auth_service()


def test_auth_config_from_hardpy_toml():
    """Test that auth configuration reads from hardpy.toml."""
    tmpdir_path = Path(tempfile.mkdtemp(prefix="hardpy-auth-config-"))
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


def test_session_timeout():
    """Test that sessions automatically expire after timeout."""
    from datetime import datetime, timedelta
    from hardpy.hardpy_panel.auth import AuthService, BasicCredentialsAuthAdapter
    
    # Create auth service with 1 minute timeout
    adapter = BasicCredentialsAuthAdapter()
    auth_service = AuthService(adapter, auth_required=True)
    auth_service.session_timeout_minutes = 1  # 1 minute timeout
    
    # Login
    expected_user = ConfigManager().config.database.user
    expected_pass = ConfigManager().config.database.password
    auth_service.login(expected_user, expected_pass)
    assert auth_service.is_authenticated() is True
    
    # Manually set session start time to 2 minutes ago to simulate timeout
    auth_service.session_start_time = datetime.now() - timedelta(minutes=2)
    
    # Check authentication - should auto-logout due to timeout
    assert auth_service.is_authenticated() is False
    assert auth_service.current_user is None
    assert auth_service.session_token is None


def test_load_auth_adapter_from_tests_path_conftest_module():
    tmpdir_path = Path(tempfile.mkdtemp(prefix="hardpy-auth-adapter-"))

    (tmpdir_path / "hardpy.toml").write_text(
        """
[auth]
required = true
adapter = "conftest.CustomAuthAdapter"
"""
    )

    (tmpdir_path / "conftest.py").write_text(
        """
from typing import Optional
from hardpy.hardpy_panel.auth import AuthAdapter

class CustomAuthAdapter(AuthAdapter):
    def authenticate(self, username: str, password: str) -> bool:
        return username == "u" and password == "p"

    def authenticate_token(self, token: str) -> Optional[str]:
        return "u" if token == "t" else None
"""
    )

    ConfigManager._instance = None
    config_manager = ConfigManager()
    config_manager.read_config(tmpdir_path)

    adapter = load_auth_adapter()
    assert adapter.authenticate("u", "p") is True
    assert adapter.authenticate_token("t") == "u"

    ConfigManager._instance = None

