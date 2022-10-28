import os
from pathlib import Path
import typing as T

import fire
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    from . import config

    app = FastAPI()

    @app.get("/server_setting")
    def get_server_setting():
        return {
            'allowed_routers': config.allowed_routers,
            'monitor_mode': config.monitor_mode,
        }

    if config.monitor_mode:
        from .routers import monitor
        app.include_router(monitor.router)
    else:
        from .routers import job, task, file
        if 'job' in config.allowed_routers:
            app.include_router(job.router)
        if 'task' in config.allowed_routers:
            app.include_router(task.router)
        if 'file' in config.allowed_routers:
            app.include_router(file.router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


OptionStrList = T.Optional[T.Union[str, T.List[str]]]


def run_server(
        host: str = "127.0.0.1",
        port: int = 5000,
        log_level: str = "info",
        frontend_addr: str = "127.0.0.1:5173",
        valid_job_type: OptionStrList = "process,thread",
        working_dir: str = ".",
        allowed_routers: OptionStrList = "task,job,file",
        monitor_mode: bool = False,
        **uvicorn_kwargs,
        ):
    from . import config

    def split_str(text: str, sep: str = "m") -> T.List[str]:
        return [t.strip() for t in text.split(sep)]
    
    def parse_str_or_list(str_or_list: T.Union[str, T.List[str]]) -> T.List[str]:
        if isinstance(str_or_list, list):
            return str_or_list
        else:
            return split_str(str_or_list)

    if frontend_addr not in config.origins:
        config.origins.append(frontend_addr)
    if valid_job_type is not None:
        config.valid_job_type = parse_str_or_list(valid_job_type)
    if allowed_routers is not None:
        config.allowed_routers = parse_str_or_list(allowed_routers)
    config.working_dir = str(Path(working_dir).absolute())
    if config.working_dir != ".":
        os.chdir(config.working_dir)
    config.monitor_mode = monitor_mode

    uvicorn_config = uvicorn.Config(
        "executor.http.server.app:create_app", factory=True,
        host=host, port=port,
        log_level=log_level,
        **uvicorn_kwargs
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


if __name__ == "__main__":
    fire.Fire(run_server)