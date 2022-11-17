from fastapi.testclient import TestClient
import pytest

from executor.http.server.app import create_app
from executor.http.server import config


@pytest.mark.order(20)
def test_turn_off_routers():
    config.allowed_routers = []
    app = create_app()
    client = TestClient(app)
    resp = client.get("/task/list_all")
    assert resp.status_code == 404
    config.allowed_routers = ['task']
    app = create_app()
    client = TestClient(app)
    resp = client.get("/task/list_all")
    assert resp.status_code == 200


@pytest.mark.order(21)
def test_get_server_setting():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/server_setting")
    assert resp.status_code == 200
    assert 'monitor_mode' in resp.json()
    assert 'allowed_routers' in resp.json()
