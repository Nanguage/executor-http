import asyncio

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server.config import ServerSetting
from executor.engine import Engine, LocalJob, ThreadJob, ProcessJob
from executor.engine import EngineSetting


def test_list_all():
    engine = Engine(setting=EngineSetting(
        cache_type="diskcache"
    ))

    async def submit_job():
        test_job_cls = [LocalJob, ThreadJob, ProcessJob]
        for job_cls in test_job_cls:
            job = job_cls(lambda: 42)
            await engine.submit_async(job)
        await engine.join()

    asyncio.run(submit_job())

    app = create_app(ServerSetting(
        monitor_mode=True,
        monitor_cache_path=engine.cache_dir
    ))
    client = TestClient(app)
    resp = client.get("/monitor/list_all")
    assert len(resp.json()) == 3

    app = create_app(ServerSetting(
        monitor_mode=True,
        monitor_cache_path=None
    ))
    client = TestClient(app)
    with pytest.raises(ValueError):
        resp = client.get("/monitor/list_all")


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

    app = create_app(ServerSetting(
        monitor_mode=True,
        monitor_cache_path=engine.cache_dir,
    ))
    client = TestClient(app)
    resp = client.get(f"/monitor/stdout/{job1.id}")
    assert resp.status_code == 200
    assert resp.json()['content'] == "hello\n"
    resp = client.get(f"/monitor/stderr/{job1.id}")
    assert resp.status_code == 200
    assert len(resp.json()['content']) > 0

    resp = client.get(f"/monitor/stdout/{job2.id}")
    assert resp.status_code == 400

    app = create_app(ServerSetting(
        monitor_mode=True,
        monitor_cache_path=None
    ))
    client = TestClient(app)
    with pytest.raises(AssertionError):
        resp = client.get(f"/monitor/stdout/{job1.id}")
