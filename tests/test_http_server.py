import typing as T
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient
import pytest

from executor.http.server.app import create_app
from executor.http.server import config
from executor.http.server.task import Task, task, TaskTable


@pytest.fixture
def task_table() -> TaskTable:
    task_table = config.task_table
    task_table.table.clear()
    return task_table


def test_task_reg_and_call(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    # test register
    def square(x: int):
        return x ** 2

    task_1 = Task(square, job_type="process")
    task_table.register(task_1)

    # test list tasks
    resp = client.get("/task/list_all", headers=headers)
    assert resp.status_code == 200
    assert 'square' in [
        t['name'] for t in resp.json()
    ]
    for t in resp.json():
        if t['name'] == 'square':
            break
    assert t['args'][0]['name'] == 'x'
    assert t['args'][0]['type'] == 'int'
    assert t['args'][0]['default'] == None
    assert t['args'][0]['range'] == None

    # test call task
    resp = client.post(
        "/task/call",
        json={
            "task_name": "square",
            "args": [2],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert 'id' in resp.json()

    # test list jobs
    resp = client.get("/job/list_all", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_cancel_and_rerun_job(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    def add(x, y):
        time.sleep(1)
        return x + y

    task_table.register(add)
    resp = client.post(
        "/task/call",
        json={
            "task_name": "add",
            "args": [1, 2],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()['status'] == "pending"
    add_id = resp.json()['id']

    resp = client.get(f"/job/cancel/{add_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['status'] == "canceled"

    resp = client.get(f"/job/re_run/{add_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['status'] == "pending"


def test_get_job_result(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task_table.register
    @task(job_type="local")
    def mul(x, y):
        time.sleep(1)
        return x * y

    resp = client.post(
        "/task/call",
        json={
            "task_name": "mul",
            "args": [40, 2],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.get(f"/job/result/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['result'] == 80


def test_errors(client: TestClient, headers: T.Optional[dict]):
    fake_job_id = "fake"
    for mth in ["status", "cancel", "re_run"]:
        resp = client.get(f"/job/{mth}/{fake_job_id}", headers=headers)
        assert resp.status_code == 400

    fake_task_name = "fake"
    resp = client.post(
        f"/task/call",
        json={
            "task_name": fake_task_name,
            "args": [],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_fetch_log(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task(job_type="local")
    def say_hello():
        print("hello")
    task_table.register(say_hello)
    resp = client.post(
        f"/task/call",
        json={
            "task_name": "say_hello",
            "args": [],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.get(f"/job/result/{job_id}", headers=headers)
    assert resp.status_code == 200
    resp = client.get(f"/job/stdout/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"


def test_remove_job(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task_table.register
    def mul_2(a, b):
        return a * b

    resp = client.post(
        f"/task/call",
        json={
            "task_name": "mul_2",
            "args": [1, 2],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.get(f"/job/remove/{job_id}", headers=headers)
    assert resp.status_code == 200
    resp = client.get("/job/list_all", headers=headers)
    assert resp.status_code == 200
    job_ids = [job['id'] for job in resp.json()]
    assert job_id not in job_ids


def test_job_condition(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task_table.register
    @task(job_type="local")
    def mul_3(a, b, c):
        return a * b * c

    resp = client.post(
        "/task/call",
        json={
            "task_name": "mul_3",
            "args": [40, 2, 1],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.post(
        "task/call",
        json={
            "task_name": "mul_3",
            "args": [21, 2, 1],
            "kwargs": {},
            "condition": {
                "type": "AfterAnother",
                "arguments": {
                    "job_id": job_id,
                    "status": "done",
                }
            }
        },
        headers=headers,
    )
    job_id = resp.json()['id']
    resp = client.get(f"/job/result/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['result'] == 42


def test_subprocess_job(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    task_table.register(Task("python -c 'print({a} + {b})'", name="cmd_add"))
    resp = client.post(
        "/task/call",
        json={
            "task_name": "cmd_add",
            "args": [],
            "kwargs": {
                "a": 1,
                "b": 2,
            }
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    time.sleep(2)
    resp = client.get(f"/job/stdout/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['content'] == "3\n\n"
    resp = client.post(
        "/task/call",
        json={
            "task_name": "cmd_add",
            "args": [],
            "kwargs": {
                "a": 1,
            }
        },
        headers=headers
    )
    assert resp.status_code == 400


def test_webapp_job(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task_table.register
    @task(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    task_table.register(Task("python -m http.server -b {ip} {port}", job_type="webapp", name="simple_httpd_cmd"))

    for task_name in ('simple_httpd', 'simple_httpd_cmd'):
        resp = client.post(
            "/task/call",
            json={
                "task_name": task_name,
                "args": [],
                "kwargs": {},
            },
            headers=headers
        )
        assert resp.status_code == 200
        job_id = resp.json()['id']
        time.sleep(5)
        resp = client.get(f"/job/status/{job_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()['status'] == "running"
        resp = client.get(f"/job/cancel/{job_id}", headers=headers)
        assert resp.status_code == 200
