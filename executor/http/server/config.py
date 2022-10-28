from .task import TaskTable


task_table = TaskTable()

valid_job_type = ['thread', 'process']

origins = [
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5000",
    "http://localhost",
]

working_dir = "."

allowed_routers = [
    "job",
    "file",
    "task",
]

monitor_mode = False
monitor_cache_path = None
