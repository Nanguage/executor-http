import typing as T
from pathlib import Path

from .task import TaskTable


task_table = TaskTable()

valid_job_types = ['thread', 'process']

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
]

monitor_mode = False
monitor_cache_path: T.Optional[T.Union[str, Path]] = None
