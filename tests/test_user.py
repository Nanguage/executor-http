from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server.user_db import crud, database, models, schemas
from executor.http.server import config
from executor.http.server.task import TaskTable
from executor.http.server import instance
from executor.engine.launcher import launcher


def login_client(client: TestClient, username: str, passwd: str):
    resp = client.post("/user/token", data={
        "username": username,
        "password": passwd,
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    token = resp.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
    }
    return headers


def test_different_user(task_table: TaskTable):
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    test_username = "user1"
    test_user_passwd = "123"
    test_user = crud.get_user_by_username_sync(db, test_username)
    if test_user is None:
        create = schemas.UserCreate(
            username=test_username,
            role="user",
            password=test_user_passwd,)
        crud.create_user(db=db, user=create)
    config.user_mode = "hub"
    config.root_password = "123"
    config.allowed_routers = ["job", "task", "file", "proxy", "user"]
    instance.reload_engine()
    app = create_app()
    client_user1 = TestClient(app)
    headers_user1 = login_client(client_user1, test_username, test_user_passwd)
    client_root = TestClient(app)
    headers_root = login_client(client_root, "root", "123")

    @task_table.register
    def add1(a):
        return a + 1

    @task_table.register
    @launcher(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    resp = client_root.post(
        "/task/call",
        json={
            "task_name": "simple_httpd",
            "args": [],
            "kwargs": {}
        },
        headers=headers_root
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client_root.post(
        "/job/wait",
        json={
            "job_id": job_id,
            "status": "running",
            "time_delta": 0.5,
        },
        headers=headers_root
    )
    assert resp.status_code == 200

    resp = client_root.get(f"/proxy/app/{job_id}/", headers=headers_root)
    assert resp.status_code == 200
    resp = client_user1.get(f"/proxy/app/{job_id}/", headers=headers_user1)
    assert resp.status_code != 200
    resp = client_root.get(f"/job/cancel/{job_id}", headers=headers_root)
    assert resp.status_code == 200

    resp = client_root.post(
        "/task/call",
        json={
            "task_name": "add1",
            "args": [1],
            "kwargs": {},
        },
        headers=headers_root,
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']

    resp = client_user1.get("/job/list_all", headers=headers_user1)
    assert len(resp.json()) == 0
    resp = client_user1.get(f"/job/status/{job_id}", headers=headers_user1)
    assert resp.status_code != 200

    resp = client_root.get("/job/list_all", headers=headers_root)
    assert len(resp.json()) == 2
    resp = client_root.get(f"/job/status/{job_id}", headers=headers_root)
    assert resp.status_code == 200
