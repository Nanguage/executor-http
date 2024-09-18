import os
import typing as T
from pathlib import Path
from dataclasses import dataclass, field

from executor.engine import EngineSetting


ValidRouters = T.Literal["job", "file", "task", "proxy", "user"]


@dataclass
class ServerSetting:
    allowed_routers: T.List[ValidRouters] = field(default_factory=lambda: [
        "job", "file", "task", "proxy",
    ])

    origins: T.List[str] = field(default_factory=lambda: [
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5000",
        "http://localhost",
        "http://localhost:5000",
        "http://localhost:5173",
        "https://nanguage.github.io",
    ])

    working_dir: T.Union[str, Path] = "."
    redirect_job_stream: bool = True
    monitor_mode: bool = False
    monitor_cache_path: T.Optional[T.Union[str, Path]] = None
    user_mode: T.Literal["free", "mono", "hub"] = "free"
    user_database_url: str = "sqlite:///./user.db"
    root_password: T.Optional[str] = os.getenv("EXECUTOR_ROOT_PASSWORD")
    jwt_secret_key: str = "91bdbf71b350475384409cef5e2103a859033f067bafbeda7467ed88d79b0e04"  # noqa: E501
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    proxy_request_wait_time: float = 0.2
    engine_setting: EngineSetting = field(default_factory=lambda: EngineSetting(  # noqa: E501
        max_jobs=None,
        print_traceback=True,
    ))
