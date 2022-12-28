import typing as T
from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient

from executor.http.server import task
from executor.http.server.task import TaskTable


def test_proxy(
        client: TestClient, task_table: TaskTable,
        headers: T.Optional[dict]):
    @task_table.register
    @task(job_type="webapp")
    def simple_httpd(ip, port):
        server_addr = (ip, port)
        httpd = HTTPServer(server_addr, SimpleHTTPRequestHandler)
        httpd.serve_forever()

    resp = client.post(
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
    resp = client.post(
        "/job/wait",
        json={
            "job_id": job_id,
            "status": "running",
            "time_delta": 0.5,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert 'address' not in resp.json()['attrs']
    resp = client.get(f"/proxy/app/{job_id}/", headers=headers)
    assert resp.status_code == 200
    resp = client.get(f"/job/cancel/{job_id}", headers=headers)
    assert resp.status_code == 200
