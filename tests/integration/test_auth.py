import json
import threading
import time
import urllib.request
import urllib.error
from urllib.request import Request

import uvicorn
import jwt

from app.main import app


def run_server(host: str = "127.0.0.1", port: int = 9061):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return server, t


def wait_until_ready(host: str, port: int, path: str = "/health", timeout_s: float = 10.0):
    """Wait until the server responds 200 on the given path."""
    started = time.time()
    while time.time() - started < timeout_s:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _post_json(url: str, payload: dict, timeout: float = 5.0):
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def test_auth_login_happy_path():
    host = "127.0.0.1"
    port = 9061
    server, thread = run_server(host, port)
    try:
        assert wait_until_ready(host, port)
        # Valid demo credentials from SecurityService
        payload = {"username": "admin", "password": "admin123"}
        with _post_json(f"http://{host}:{port}/api/v1/auth/login", payload, timeout=10) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            # Basic TokenResponse shape
            assert set(["access_token", "refresh_token", "token_type", "expires_in"]).issubset(body.keys())
            assert body["token_type"] == "bearer"
            assert isinstance(body["expires_in"], int) and 0 < body["expires_in"] <= 3600
            # Decode JWT without verifying signature to inspect claims
            decoded = jwt.decode(body["access_token"], options={"verify_signature": False})
            assert decoded.get("sub") == "admin"
            assert decoded.get("username") == "admin"
            assert decoded.get("exp") > decoded.get("iat")
    finally:
        server.should_exit = True
        thread.join(timeout=2)


def test_auth_login_validation_errors_422():
    host = "127.0.0.1"
    port = 9062
    server, thread = run_server(host, port)
    try:
        assert wait_until_ready(host, port)
        # Invalid: username too short, password too short
        payload = {"username": "ab", "password": "short"}
        try:
            _post_json(f"http://{host}:{port}/api/v1/auth/login", payload)
            assert False, "Expected HTTPError 422"
        except urllib.error.HTTPError as e:
            assert e.code == 422
            detail = e.read().decode()
            assert "username" in detail or "password" in detail
    finally:
        server.should_exit = True
        thread.join(timeout=2)


def test_auth_login_wrong_credentials_401():
    host = "127.0.0.1"
    port = 9063
    server, thread = run_server(host, port)
    try:
        assert wait_until_ready(host, port)
        payload = {"username": "admin", "password": "wrongpass"}
        try:
            _post_json(f"http://{host}:{port}/api/v1/auth/login", payload)
            assert False, "Expected HTTPError 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        server.should_exit = True
        thread.join(timeout=2)

