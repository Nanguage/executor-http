from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server.config import ServerSetting
from executor.http.server.user_db import crud, database, models, schemas
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


def test_error_password():
    app = create_app(ServerSetting(
        user_mode="hub",
        root_password="123",
        allowed_routers=["job", "task", "file", "proxy", "user"],
    ))

    client = TestClient(app)
    resp = client.post("/user/token", data={
        "username": "fake",
        "password": "fake",
    })
    assert resp.status_code == 401


def test_login_with_fake_token():
    app = create_app(ServerSetting(
        user_mode="hub",
        root_password="123",
        allowed_routers=["job", "task", "file", "proxy", "user"],
    ))
    client = TestClient(app)
    fake_headers = {
        "Authorization": "Bearer fake"
    }
    resp = client.get("/user/info", headers=fake_headers)
    assert resp.status_code == 401


def create_db_for_test(engine):
    models.Base.metadata.create_all(bind=engine)
    db = database.get_local_session(engine)
    test_username = "user1"
    test_user_passwd = "123"
    test_user = crud.get_user_by_username_sync(db, test_username)
    if test_user is None:
        create = schemas.UserCreate(
            username=test_username,
            role="user",
            password=test_user_passwd,)
        crud.create_user(db=db, user=create)
    return test_username, test_user_passwd


def test_different_user():
    app = create_app(ServerSetting(
        user_mode="hub",
        root_password="123",
        allowed_routers=["job", "task", "file", "proxy", "user"],
    ))
    task_table = app.task_table
    db_engine = database.get_engine(app.config.user_database_url)
    test_username, test_user_passwd = create_db_for_test(db_engine)

    client = TestClient(app)
    headers_user1 = login_client(client, test_username, test_user_passwd)
    headers_root = login_client(client, "root", "123")

    resp = client.get("/user/info", headers=headers_user1)
    assert resp.status_code == 200
    assert resp.json()['username'] == 'user1'
    resp = client.get("/user/info", headers=headers_root)
    assert resp.status_code == 200
    assert resp.json()['username'] == 'root'

    @task_table.register
    def add1(a):
        return a + 1

    @task_table.register
    @launcher(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    resp = client.post(
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
    resp = client.post(
        "/job/wait",
        json={
            "job_id": job_id,
            "statuses": ["running"],
            "time_delta": 0.5,
        },
        headers=headers_root
    )
    assert resp.status_code == 200

    resp = client.get(f"/proxy/app/{job_id}/", headers=headers_root)
    assert resp.status_code == 200
    resp = client.get(f"/proxy/app/{job_id}/", headers=headers_user1)
    assert resp.status_code != 200
    resp = client.get(f"/job/cancel/{job_id}", headers=headers_root)
    assert resp.status_code == 200

    resp = client.post(
        "/task/call",
        json={
            "task_name": "add1",
            "args": [1],
            "kwargs": {},
        },
        headers=headers_user1,
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']

    resp = client.get("/job/list_all", headers=headers_user1)
    assert len(resp.json()) == 1
    resp = client.get(f"/job/status/{job_id}", headers=headers_root)
    assert resp.status_code == 200

    resp = client.get("/job/list_all", headers=headers_root)
    assert len(resp.json()) == 2
    resp = client.get(f"/job/status/{job_id}", headers=headers_root)
    assert resp.status_code == 200
