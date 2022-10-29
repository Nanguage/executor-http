import asyncio

from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config
from executor.engine import Engine, LocalJob, ThreadJob, ProcessJob


def test_monitor_server():
    engine = Engine()

    async def submit_job():
        test_job_cls = [LocalJob, ThreadJob, ProcessJob]
        for job_cls in test_job_cls:
            job = job_cls(lambda: 42)
            await engine.submit(job)
        await engine.wait()

    asyncio.run(submit_job())
    config.monitor_mode = True
    config.monitor_cache_path = engine.cache_dir / "jobs"

    app = create_app()
    client = TestClient(app)
    resp = client.get("/monitor/list_all")
    assert len(resp.json()) == 3
