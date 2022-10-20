import time
import os

from fastapi.testclient import TestClient
import pytest

from executor.http.server.app import create_app
from executor.http.server.config import task_table, valid_job_type
from executor.http.server.task import Task

app = create_app()


client = TestClient(app)


@pytest.mark.order(0)
def test_register_task():
    def square(x: int):
        return x ** 2

    task_table.register(Task(square, name='square'))


@pytest.mark.order(1)
def test_list_tasks():
    resp = client.get("/task/list_all")
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


@pytest.mark.order(2)
def test_get_valid_job_types():
    resp = client.get("/job/valid_types")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.order(3)
def test_call_task():
    resp = client.post(
        "/task/call",
        json={
            "task_name": "square",
            "args": [2],
            "kwargs": {},
            "job_type": "thread",
        },
    )
    assert resp.status_code == 200
    assert 'id' in resp.json()


@pytest.mark.order(4)
def test_get_all_jobs():
    resp = client.get("/job/list_all")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.order(5)
def test_cancel_and_rerun_job():
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
            "job_type": "thread",
        }
    )
    assert resp.status_code == 200
    assert resp.json()['status'] == "pending"
    add_id = resp.json()['id']

    resp = client.get(f"/job/cancel/{add_id}")
    assert resp.status_code == 200
    assert resp.json()['status'] == "canceled"

    resp = client.get(f"/job/re_run/{add_id}")
    assert resp.status_code == 200
    assert resp.json()['status'] == "pending"


@pytest.mark.order(6)
def test_get_job_result():
    def mul(x, y):
        time.sleep(1)
        return x * y
    
    task_table.register(mul)
    valid_job_type.append('local')
    resp = client.post(
        "/task/call",
        json={
            "task_name": "mul",
            "args": [40, 2],
            "kwargs": {},
            "job_type": "local",
        }
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.get(f"/job/result/{job_id}")
    assert resp.status_code == 200
    assert resp.json()['result'] == 80


@pytest.mark.order(7)
def test_errors():
    fake_job_id = "fake"
    for mth in ["status", "cancel", "re_run"]:
        resp = client.get(f"/job/{mth}/{fake_job_id}")
        assert resp.status_code == 400

    fake_task_name = "fake"
    resp = client.post(
        f"/task/call",
        json={
            "task_name": fake_task_name,
            "args": [],
            "kwargs": {},
            "job_type": "local",
        }
    )
    assert resp.status_code == 400

    def mul_2(x, y):
        return x * y
    task_table.register(mul_2)
    valid_job_type.clear()
    valid_job_type.append("thread")
    resp = client.post(
        f"/task/call",
        json={
            "task_name": "mul_2",
            "args": [1, 2],
            "kwargs": {},
            "job_type": "local",
        }
    )
    assert resp.status_code == 400


@pytest.mark.order(8)
def test_fetch_log():
    valid_job_type.append("local")
    def say_hello():
        print("hello")
    task_table.register(say_hello)
    resp = client.post(
        f"/task/call",
        json={
            "task_name": "say_hello",
            "args": [],
            "kwargs": {},
            "job_type": "local",
        }
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.get(f"/job/result/{job_id}")
    assert resp.status_code == 200
    resp = client.get(f"/job/stdout/{job_id}")
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"


@pytest.mark.order(9)
def test_list_dir():
    resp = client.post(
        "/file/list_dir",
        json={
            "path": ""
        }
    )
    assert resp.status_code == 200
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "not_exists"
        }
    )
    assert resp.status_code == 404
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "../../"
        }
    )
    assert resp.status_code == 403


@pytest.mark.order(10)
def test_download_file():
    test_file = "for_download.txt"
    with open(test_file, 'w') as f:
        f.write("123")
    resp = client.post("/file/download", json={"path": test_file})
    assert resp.status_code == 200
    os.remove(test_file)    
