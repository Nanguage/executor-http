from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config, task_table, task


def test_proxy():
    config.monitor_mode = False
    config.monitor_cache_path = None
    config.allowed_routers = ["task", "job", "file", "proxy"]
    app = create_app()
    client = TestClient(app)

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
        }
    )
    assert resp.status_code == 200
    job_id = resp.json()['id']
    resp = client.post(
        "/job/wait",
        json={
            "job_id": job_id,
            "status": "running",
            "time_delta": 0.5,
        }
    )
    assert resp.status_code == 200
    assert 'address' not in resp.json()['attrs']
    resp = client.get(f"/proxy/app/{job_id}")
    assert resp.status_code == 200
    resp = client.get(f"/job/cancel/{job_id}")
    assert resp.status_code == 200
