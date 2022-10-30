import asyncio

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config
from executor.engine import Engine, LocalJob, ThreadJob, ProcessJob


def test_list_all():
    engine = Engine()

    async def submit_job():
        test_job_cls = [LocalJob, ThreadJob, ProcessJob]
        for job_cls in test_job_cls:
            job = job_cls(lambda: 42)
            await engine.submit(job)
        await engine.wait()

    asyncio.run(submit_job())
    config.monitor_mode = True
    config.monitor_cache_path = engine.cache_dir

    app = create_app()
    client = TestClient(app)
    resp = client.get("/monitor/list_all")
    assert len(resp.json()) == 3


def test_fetch_log():
    def say_hello():
        print("hello")

    engine = Engine()
    job = LocalJob(say_hello, redirect_out_err=True)

    async def submit_job():
        await engine.submit(job)
        await engine.wait()

    asyncio.run(submit_job())

    config.monitor_cache_path = engine.cache_dir
    app = create_app()
    client = TestClient(app)
    resp = client.get(f"/monitor/stdout/{job.id}")
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"
