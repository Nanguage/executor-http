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

    if config.user_mode != "free":
        from .user_db.crud import init_db
        init_db()

    if config.monitor_mode:
        from .routers import monitor
        app.include_router(monitor.router)
    else:
        from .routers import job, task, file, user
        if 'job' in config.allowed_routers:
            app.include_router(job.router)
        if 'task' in config.allowed_routers:
            app.include_router(task.router)
        if 'file' in config.allowed_routers:
            app.include_router(file.router)
        if 'user' in config.allowed_routers:
            app.include_router(user.router)

    if 'proxy' in config.allowed_routers:
        from .routers import proxy
        app.include_router(proxy.router)
        app.get("/{path:path}")(proxy.root_dispatch)
        app.post("/{path:path}")(proxy.root_dispatch)

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
        working_dir: T.Optional[T.Union[str, Path]] = ".",
        allowed_routers: OptionStrList = None,
        monitor_mode: T.Optional[bool] = None,
        monitor_cache_path: T.Optional[str] = None,
        **uvicorn_kwargs,
        ):
    from . import config

    def split_str(text: str, sep: str = ",") -> T.List[str]:
        return [t.strip() for t in text.split(sep)]
    
    def parse_str_or_list(str_or_list: T.Union[str, T.List[str]]) -> T.List[str]:
        if isinstance(str_or_list, list):
            return str_or_list
        else:
            return split_str(str_or_list)

    if frontend_addr not in config.origins:
        config.origins.append(frontend_addr)
    if allowed_routers is not None:
        config.allowed_routers = parse_str_or_list(allowed_routers)
    if working_dir is not None:
        config.working_dir = str(Path(working_dir).absolute())
    if monitor_mode is not None:
        config.monitor_mode = monitor_mode
    if monitor_cache_path is not None:
        config.monitor_cache_path  = monitor_cache_path

    if str(config.working_dir) != ".":
        working_dir = Path(config.working_dir)
        os.chdir(working_dir)

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