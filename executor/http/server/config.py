import os
import typing as T
from pathlib import Path

from .task import TaskTable


task_table = TaskTable()

origins = [
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5000",
    "http://localhost",
]

working_dir: T.Union[str, Path] = "."

allowed_routers = [
    "job",
    "file",
    "task",
    "proxy",
]

# redirect job's stdout and stderr to file or not
redirect_job_stream: bool = True

monitor_mode = False
monitor_cache_path: T.Optional[T.Union[str, Path]] = None

user_mode: T.Literal["free", "mono", "hub"] = "free"
user_database_url = "sqlite:///./user.db"
root_password = os.environ.get("EXECUTOR_ROOT_PASSWORD")

# Secret key for JSON Web Token
# Generate using command: openssl rand -hex 32
jwt_secret_key = "91bdbf71b350475384409cef5e2103a859033f067bafbeda7467ed88d79b0e04"  # noqa: E501
jwt_algorithm = "HS256"

access_token_expire_minutes = 30

# The reverse_proxy wait time between two calls
proxy_request_wait_time = 0.2
