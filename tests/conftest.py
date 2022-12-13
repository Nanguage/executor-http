import typing as T
import shutil
import os.path
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config
from executor.http.server import auth


def pytest_sessionfinish(session, exitstatus):
    # clear root user dir
    root_user_path = "root/"
    if os.path.exists(root_user_path):
        shutil.rmtree(root_user_path)


@pytest.fixture(params=["free", "hub"])
def client(request) -> TestClient:
    mode = request.param
    routers_for_test = ["job", "task", "file"]
    if mode == "free":
        config.user_mode = "free"
        config.allowed_routers = routers_for_test
        auth.reload()
    else:
        config.allowed_routers = routers_for_test + ["user"]
        config.user_mode = "hub"
        config.root_password = "123"
        auth.reload()
    app = create_app()
    app.user_mode = mode
    client = TestClient(app)
    return client


@pytest.fixture
def headers(client: TestClient) -> T.Optional[dict]:
    if client.app.user_mode == "free":
        return None
    else:
        resp = client.post("/user/login", data={
            "username": "root",
            "password": "123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        token = resp.json()["access_token"]
        res = {
            "Authorization": f"Bearer {token}", 
        }
        return res


@pytest.fixture
def base_path(client: TestClient) -> Path:
    if client.app.user_mode == "free":
        return Path(".")
    else:
        return Path("root/")
