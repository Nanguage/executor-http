import typing as T

from executor.engine.launcher import (
    LauncherBase, AsyncLauncher,
    SyncLauncher,
)
from funcdesc.desc import NotDef


class TaskTable(object):
    def __init__(
            self,
            table: T.Optional[T.Dict[str, AsyncLauncher]] = None) -> None:
        self.table: T.Dict[str, AsyncLauncher] = table or {}

    def __getitem__(self, key: str) -> AsyncLauncher:
        return self.table[key]

    def register(self, task: T.Union[LauncherBase, T.Callable]):
        if isinstance(task, SyncLauncher):
            task = task.to_async()
        elif isinstance(task, AsyncLauncher):
            task = task
        else:
            task = AsyncLauncher(task)
        self.table[task.name] = task

    @staticmethod
    def task_to_dict(task: AsyncLauncher) -> dict:
        args = []
        for arg in task.desc.inputs:
            default = arg.default
            if default is NotDef:
                default = None
            if hasattr(arg.type, "__name__"):
                type_name = arg.type.__name__
            else:
                type_name = str(arg.type)
            args.append({
                "name": arg.name,
                "type": type_name,
                "default": default,
                "range": arg.range,
            })
        return {
            "name": task.name,
            "description": task.description,
            "args": args,
            "attrs": task.job_attrs,
        }
