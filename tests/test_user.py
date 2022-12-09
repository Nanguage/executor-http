import typing as T

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config


@pytest.fixture
def client():
    config.user_mode = "hub"
    config.root_password = "123"
    config.allowed_routers = ["user", "task", "job", "file"]
    app = create_app()
    client = TestClient(app)
    return client


@pytest.fixture
def client_and_token(client: TestClient):
    resp = client.post("/user/login", data={
        "username": "root",
        "password": "123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    token = resp.json()["access_token"]
    return (client, token)


def get_auth_header(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}", 
    }


def test_file_router(client_and_token: T.Tuple[TestClient, str]):
    client, token = client_and_token
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "."
        },
        headers=get_auth_header(token),
    )
    assert resp.status_code == 200
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "not_exists"
        },
        headers=get_auth_header(token),
    )
    assert resp.status_code == 404
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "../../"
        },
        headers=get_auth_header(token),
    )
    assert resp.status_code == 403

