import typing as T
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest
from httpx import AsyncClient

from executor.http.server.task import TaskTable
from executor.engine.launcher import launcher


@pytest.mark.asyncio
async def test_proxy(
        async_client: AsyncClient,
        async_get_headers: T.Awaitable[T.Optional[dict]]):
    task_table: TaskTable = async_client.app.task_table

    @task_table.register
    @launcher(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    @task_table.register
    @launcher(job_type="process")
    def add(a, b):
        time.sleep(2)
        return a + b

    headers = await async_get_headers

    resp = await async_client.post(
        "/task/call",
        json={
            "task_name": "simple_httpd",
            "args": [],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']

    resp = await async_client.post(
        "/job/wait",
        json={
            "job_id": job_id,
            "statuses": ["running"],
            "time_delta": 0.5,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert 'address' not in resp.json()['attrs']

    resp = await async_client.get(
        f"/proxy/app/{job_id}/", headers=headers)
    assert resp.status_code == 200

    # proxy a job doesn't exist
    resp = await async_client.get(
        "/proxy/app/not_exist/", headers=headers)
    assert resp.status_code == 400

    resp = await async_client.get(
        f"/job/cancel/{job_id}", headers=headers)
    assert resp.status_code == 200

    # proxy a not running job
    resp = await async_client.get(
        f"/proxy/app/{job_id}/", headers=headers)
    assert resp.status_code == 400

    # proxy a job that is not a webapp
    resp = await async_client.post(
        "/task/call",
        json={
            "task_name": "add",
            "args": [1, 2],
            "kwargs": {},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = await async_client.get(
        f"/proxy/app/{job_id}/", headers=headers)
    assert resp.status_code == 400
    resp = await async_client.get(
        f"/job/cancel/{job_id}", headers=headers)
    assert resp.status_code == 200
