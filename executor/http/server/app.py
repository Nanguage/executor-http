import typing as T

import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from .config import ServerSetting
from .task import TaskTable
from .utils import CustomFastAPI

from executor.engine import Engine


def create_app(
        server_setting: T.Optional[ServerSetting] = None,
        task_table: T.Optional[TaskTable] = None,
        engine: T.Optional[Engine] = None,
        ) -> CustomFastAPI:
    if server_setting is None:
        server_setting = ServerSetting()
    if task_table is None:
        task_table = TaskTable()
    if engine is None:
        engine = Engine(server_setting.engine_setting)

    app = CustomFastAPI()
    app.config = server_setting
    app.task_table = task_table
    app.engine = engine
    app.db_engine = None

    @app.get("/server_setting")
    def get_server_setting():
        return {
            'allowed_routers': app.config.allowed_routers,
            'monitor_mode': app.config.monitor_mode,
            'user_mode': app.config.user_mode,
        }

    if app.config.user_mode != "free":
        from .user_db.crud import init_db
        from .user_db.database import get_async_engine
        init_db(
            app.config.root_password,
            app.config.user_database_url
        )
        app.db_engine = get_async_engine(
            app.config.user_database_url
        )

    if app.config.monitor_mode:
        from .routers import monitor
        app.include_router(monitor.router)
    else:
        from .routers import job, task, file, user
        if 'job' in app.config.allowed_routers:
            app.include_router(job.router)
        if 'task' in app.config.allowed_routers:
            app.include_router(task.router)
        if 'file' in app.config.allowed_routers:
            app.include_router(file.router)
        if 'user' in app.config.allowed_routers:
            app.include_router(user.router)

    def include_proxy_router():
        from .routers import proxy
        app.include_router(proxy.router)
        app.get("/{path:path}")(proxy.root_dispatch)
        app.post("/{path:path}")(proxy.root_dispatch)

    if 'proxy' in app.config.allowed_routers:
        include_proxy_router()

    app.include_proxy_router = include_proxy_router

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.config.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def run_app(
        app: CustomFastAPI,
        host: str = "127.0.0.1",
        port: int = 5000,
        log_level: str = "info",
        **other_uvicorn_kwargs,
        ):  # pragma: no cover
    uvicorn.run(
        app, host=host, port=port, log_level=log_level,
        **other_uvicorn_kwargs
    )
