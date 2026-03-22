from fastapi.testclient import TestClient
import os

from hardpy.hardpy_panel.api import app
from hardpy.hardpy_panel.auth import make_auth_service

client = TestClient(app)


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
    os.environ["HARDPY_AUTH_ADAPTER"] = "hardpy.hardpy_panel.auth.DummyAuthAdapter"
    os.environ["HARDPY_AUTH_REQUIRED"] = "true"

    app.state.auth_service = make_auth_service()
    app.state.auth_service.logout()

    with TestClient(app) as client_local:
        bad_resp = client_local.post("/api/login", json={"username": "notdummy", "password": "nope"})
        assert bad_resp.status_code == 401

        good_resp = client_local.post("/api/login", json={"username": "dummy", "password": "dummy"})
        assert good_resp.status_code == 200
        assert good_resp.json()["status"] == "success"
        assert app.state.auth_service.current_user == "dummy"

        start_resp = client_local.get("/api/start")
        assert start_resp.status_code != 401

    del os.environ["HARDPY_AUTH_ADAPTER"]
    del os.environ["HARDPY_AUTH_REQUIRED"]
    app.state.auth_service = make_auth_service()
