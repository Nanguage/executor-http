import os
from pathlib import Path

import fire
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



def create_app() -> FastAPI:
    from .routers import job, task, file
    from . import config

    app = FastAPI()
    app.include_router(job.router)
    app.include_router(task.router)
    app.include_router(file.router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def run_server(
        host: str = "127.0.0.1",
        port: int = 5000,
        log_level: str = "info",
        frontend_addr: str = "127.0.0.1:5173",
        valid_job_type: str = "process,thread",
        working_dir: str = ".",
        **kwargs,
        ):
    from . import config

    if frontend_addr not in config.origins:
        config.origins.append(frontend_addr)
    if valid_job_type:
        config.valid_job_type = valid_job_type.split(",")
    config.working_dir = str(Path(working_dir).absolute())
    if config.working_dir != ".":
        os.chdir(config.working_dir)
    uvicorn_config = uvicorn.Config(
        "executor.http.server.app:create_app", factory=True,
        host=host, port=port,
        log_level=log_level,
        **kwargs
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


if __name__ == "__main__":
    fire.Fire(run_server)