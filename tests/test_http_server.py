import typing as T
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from cmd2func import cmd2func

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from executor.http.server.task import TaskTable
from executor.http.server.app import CustomFastAPI
from executor.engine.launcher import launcher


def test_task_reg_and_call(
        client: TestClient, headers: T.Optional[dict]):
    task_table: TaskTable = client.app.task_table

    # test register
    def square(x: int):
        return x ** 2

    task_1 = launcher(square, job_type="process")
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
    assert t['args'][0]['default'] is None
    assert t['args'][0]['range'] is None

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
        client: TestClient, headers: T.Optional[dict]):

    task_table: TaskTable = client.app.task_table

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

    # test the error of rerun a pending job
    resp = client.get(f"/job/re_run/{add_id}", headers=headers)
    assert resp.status_code == 400

    resp = client.get(f"/job/cancel/{add_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['status'] == "cancelled"

    # test the error of cancel a cancelled job
    resp = client.get(f"/job/cancel/{add_id}", headers=headers)
    assert resp.status_code == 400

    resp = client.get(f"/job/re_run/{add_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['status'] == "pending"


@pytest.mark.asyncio
async def test_get_job_result(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    task_table: TaskTable = async_client.app.task_table

    @task_table.register
    @launcher(job_type="local")
    def mul(x, y):
        time.sleep(1)
        return x * y

    headers = await async_get_headers

    resp = await async_client.post(
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
    resp = await async_client.get(
        f"/job/result/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['result'] == 80


def test_errors(client: TestClient, headers: T.Optional[dict]):
    fake_job_id = "fake"
    for mth in ["status", "cancel", "re_run"]:
        resp = client.get(f"/job/{mth}/{fake_job_id}", headers=headers)
        assert resp.status_code == 400

    fake_task_name = "fake"
    resp = client.post(
        "/task/call",
        json={
            "task_name": fake_task_name,
            "args": [],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_fetch_log(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    app: CustomFastAPI = async_client.app
    task_table: TaskTable = app.task_table

    @launcher(job_type="local")
    def say_hello():
        print("hello")
        raise Exception("error")
    task_table.register(say_hello)

    headers = await async_get_headers
    resp = await async_client.post(
        "/task/call",
        json={
            "task_name": "say_hello",
            "args": [],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = await async_client.post("/job/wait", json={
        "job_id": job_id
    }, headers=headers)
    assert resp.status_code == 200
    resp = await async_client.get(f"/job/stdout/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"
    resp = await async_client.get(f"/job/stderr/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()['content']) > 0


@pytest.mark.asyncio
async def test_fetch_log_error(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    app: CustomFastAPI = async_client.app
    task_table: TaskTable = app.task_table
    # turn-off redirect stream, test the read error
    app.config.redirect_job_stream = False

    @launcher(job_type="local")
    def say_hello():
        print("hello")
    task_table.register(say_hello)

    headers = await async_get_headers

    resp = await async_client.post(
        "/task/call",
        json={
            "task_name": "say_hello",
            "args": [],
            "kwargs": {},
        },
        headers=headers
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = await async_client.post("/job/wait", json={
        "job_id": job_id
    }, headers=headers)
    assert resp.status_code == 200
    resp = await async_client.get(f"/job/stdout/{job_id}", headers=headers)
    assert resp.status_code == 400


def test_remove_job(
        client: TestClient,
        headers: T.Optional[dict]):
    task_table: TaskTable = client.app.task_table

    @task_table.register
    def mul_2(a, b):
        return a * b

    resp = client.post(
        "/task/call",
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


@pytest.mark.asyncio
async def test_job_condition(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    task_table: TaskTable = async_client.app.task_table

    @task_table.register
    @launcher(job_type="local")
    def mul_3(a, b, c):
        return a * b * c

    headers = await async_get_headers

    resp = await async_client.post(
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
    resp = await async_client.post(
        "task/call",
        json={
            "task_name": "mul_3",
            "args": [21, 2, 1],
            "kwargs": {},
            "condition": {
                "type": "AfterAnother",
                "arguments": {
                    "job_id": job_id,
                }
            }
        },
        headers=headers,
    )
    job_id = resp.json()['id']
    resp = await async_client.get(
        f"/job/result/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['result'] == 42

    # test AfterOthers(not supported)
    resp = await async_client.post(
        "task/call",
        json={
            "task_name": "mul_3",
            "args": [21, 2, 1],
            "kwargs": {},
            "condition": {
                "type": "AfterOthers",
                "arguments": {
                    "jobs_id": [job_id],
                }
            }
        },
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_subprocess_job(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    task_table: TaskTable = async_client.app.task_table

    @launcher
    @cmd2func
    def cmd_add(a, b):
        return f"python -c 'print({a} + {b})'"
    task_table.register(cmd_add)

    headers = await async_get_headers

    resp = await async_client.post(
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
    resp = await async_client.post(
        "/job/wait",
        json={
            "job_id": job_id,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    resp = await async_client.get(
        f"/job/stdout/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()['content'].strip() == "3"
    resp = await async_client.post(
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
        client: TestClient,
        headers: T.Optional[dict]):
    task_table: TaskTable = client.app.task_table

    @task_table.register
    @launcher(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    @task_table.register
    @launcher(job_type="webapp")
    @cmd2func
    def simple_httpd_cmd():
        return "python -m http.server -b {ip} {port}"

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


def test_register_job(
        client: TestClient,
        headers: T.Optional[dict]):
    task_table: TaskTable = client.app.task_table

    @task_table.register
    @launcher(job_type="local", async_mode=True)
    def mul_4(a: 'int', b: int, c: int):
        return a * b * c

    resp = client.post(
        "/task/call",
        json={
            "task_name": "mul_4",
            "args": [40, 2, 1],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    resp = client.get("/task/list_all", headers=headers)
    assert resp.status_code == 200
