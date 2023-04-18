from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server.config import ServerSetting


def test_turn_off_routers():
    app = create_app(ServerSetting(
        allowed_routers=[]
    ))
    client = TestClient(app)
    resp = client.get("/task/list_all")
    assert resp.status_code == 404
    app = create_app(ServerSetting(
        allowed_routers=['task']
    ))
    client = TestClient(app)
    resp = client.get("/task/list_all")
    assert resp.status_code == 200


def test_get_server_setting():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/server_setting")
    assert resp.status_code == 200
    assert 'monitor_mode' in resp.json()
    assert 'allowed_routers' in resp.json()
