import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config, task_table, task


config.allowed_routers = ["task", "job", "file", "proxy"]
app = create_app()

client = TestClient(app)


def test_proxy():
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
    time.sleep(5)
    job_id = resp.json()['id']
    resp = client.get(f"/proxy/app/{job_id}")
    assert resp.status_code == 200
    resp = client.get(f"/job/cancel/{job_id}")
    assert resp.status_code == 200
