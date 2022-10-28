from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config


def test_turn_off_routers():
    config.allowed_routers = []
    app = create_app()
    client = TestClient(app)
    resp = client.get("task/list_all")
    assert resp.status_code == 404
    config.allowed_routers = ['task']
    app = create_app()
    client = TestClient(app)
    resp = client.get("task/list_all")
    assert resp.status_code == 200


def test_get_server_setting():
    config.valid_job_types = ['thread', 'process']
    app = create_app()
    client = TestClient(app)
    resp = client.get("/server_setting")
    assert resp.status_code == 200
    assert 'monitor_mode' in resp.json()
    assert 'allowed_routers' in resp.json()
    assert len(resp.json()['valid_job_types']) == 2
