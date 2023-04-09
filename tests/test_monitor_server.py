import asyncio

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config
from executor.engine import Engine, LocalJob, ThreadJob, ProcessJob


@pytest.mark.order(-2)
def test_list_all():
    engine = Engine()

    async def submit_job():
        test_job_cls = [LocalJob, ThreadJob, ProcessJob]
        for job_cls in test_job_cls:
            job = job_cls(lambda: 42)
            await engine.submit_async(job)
        await engine.join()

    asyncio.run(submit_job())
    config.allowed_routers = []
    config.monitor_mode = True
    config.monitor_cache_path = engine.cache_dir

    app = create_app()
    client = TestClient(app)
    resp = client.get("/monitor/list_all")
    assert len(resp.json()) == 3


@pytest.mark.order(-1)
def test_fetch_log():
    def say_hello():
        print("hello")
        raise Exception("error")

    engine = Engine()
    job1 = LocalJob(say_hello, redirect_out_err=True)
    job2 = LocalJob(say_hello, redirect_out_err=False)

    async def submit_job():
        await engine.submit_async(job1, job2)
        await engine.join()

    asyncio.run(submit_job())

    config.monitor_cache_path = engine.cache_dir
    app = create_app()
    client = TestClient(app)
    resp = client.get(f"/monitor/stdout/{job1.id}")
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"
    resp = client.get(f"/monitor/stderr/{job1.id}")
    assert resp.status_code == 200
    assert len(resp.json()['content']) > 0

    resp = client.get(f"/monitor/stdout/{job2.id}")
    assert resp.status_code == 400

    config.monitor_cache_path = None
    app = create_app()
    client = TestClient(app)
    resp = client.get(f"/monitor/stdout/{job1.id}")
    assert resp.status_code == 400
