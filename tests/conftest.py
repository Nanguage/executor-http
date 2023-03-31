import sys
import os
import typing as T
import shutil
from os.path import exists, join, abspath
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

if T.TYPE_CHECKING:
    from executor.http.server.task import TaskTable


def pytest_sessionstart(session):
    sys.path.insert(0, abspath(join(__file__, "../../")))
    # remove proxy env
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''


def pytest_sessionfinish(session, exitstatus):
    # clear root user dir
    root_user_path = "root/"
    if exists(root_user_path):
        shutil.rmtree(root_user_path)


def _get_app(request):
    from executor.http.server.app import create_app
    from executor.http.server import config
    from executor.http.server import utils

    mode = request.param
    routers_for_test = ["job", "task", "file", "proxy"]
    if mode == "free":
        config.user_mode = "free"
        config.allowed_routers = routers_for_test
        utils.reload_routers()
    else:
        config.allowed_routers = routers_for_test + ["user"]
        config.user_mode = "hub"
        config.root_password = "123"
        utils.reload_routers()
    app = create_app()
    app.user_mode = mode
    return app


@pytest.fixture(params=["free", "hub"])
def async_client(request):
    app = _get_app(request)
    client = AsyncClient(app=app, base_url="http://test")
    client.app = app
    return client


@pytest.fixture(params=["free", "hub"])
def client(request) -> TestClient:
    app = _get_app(request)
    client = TestClient(app)
    return client


def _get_header_from_respond(resp) -> dict:
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    token = resp.json()["access_token"]
    res = {
        "Authorization": f"Bearer {token}",
    }
    return res


@pytest.fixture
def headers(client: TestClient) -> T.Optional[dict]:
    if client.app.user_mode == "free":
        return None
    else:
        resp = client.post("/user/token", data={
            "username": "root",
            "password": "123",
        })
        return _get_header_from_respond(resp)


@pytest.fixture
async def async_get_headers(
        async_client: AsyncClient) -> T.Optional[dict]:
    if async_client.app.user_mode == "free":
        return None
    else:
        resp = await async_client.post("/user/token", data={
            "username": "root",
            "password": "123",
        })
        return _get_header_from_respond(resp)


@pytest.fixture
def base_path(client: TestClient) -> Path:
    if client.app.user_mode == "free":
        return Path(".")
    else:
        return Path("root/")


@pytest.fixture
def task_table() -> "TaskTable":
    from executor.http.server import config
    task_table = config.task_table
    task_table.table.clear()
    return task_table
