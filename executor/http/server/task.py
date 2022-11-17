import typing as T
import functools

from oneface.arg import parse_func_args, Empty
from executor.engine.job import Job
from executor.engine.job.condition import Condition

from .utils import JobType, jobtype_classes, Command, print_error


class Task(object):
    def __init__(
            self, target: T.Union[T.Callable, str],
            name: T.Optional[str] = None,
            description: str = "",
            job_type: T.Optional[JobType] = None,
            **kwargs
            ):
        self.target: T.Union[T.Callable, Command]
        if isinstance(target, str):
            command = Command(target)
            self.target = command
            self.name = name or command.name
            self.args = self.get_command_args(command)
            if not description:
                description = f"Run command: {target}"
        else:
            self.target = target
            func: T.Callable = target
            self.name = name or func.__name__
            self.args = self.get_func_args(func)
            if not description:
                if hasattr(func, "__doc__") and (func.__doc__ is not None):
                    description = func.__doc__
        if job_type is None:
            if isinstance(self.target, Command):
                job_type = "subprocess"
            else:
                job_type = "process"

        self.description = description
        self.job_type = job_type
        if isinstance(self.target, Command):
            if self.job_type not in ("subprocess", "webapp"):
                raise ValueError("Command only support subprocess and webapp job type.")
        self.attrs = kwargs

    def create_job(self, args: T.Tuple, kwargs: T.Dict, condition: Condition) -> Job:
        job_cls: T.Type[Job] = jobtype_classes[self.job_type]

        job_kwargs = {
            "callback": None,
            "error_callback": print_error,
            "name": self.name,
            "redirect_out_err": True,
            "condition": condition,
        }

        if isinstance(self.target, Command):
            cmd = self.target.format(kwargs)
            job = job_cls(cmd, **job_kwargs)
        else:
            job = job_cls(self.target, args=args, kwargs=kwargs, **job_kwargs)
        return job

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "args": self.args,
            "attrs": self.attrs,
        }

    @staticmethod
    def get_func_args(func: T.Callable) -> T.List[dict]:
        """Return JSON serializable argument information for frontend."""
        args = []
        arg_objs = parse_func_args(func)
        for name, o in arg_objs.items():
            default = None if o.default is Empty else o.default
            if o.type is Empty:
                o.type = str  # set default type to str
            type_name = str(o.type)
            if hasattr(o.type, "__name__"):
                type_name = o.type.__name__
            arg = {
                "name": name,
                "type": type_name,
                "range": o.range,
                "default": default,
            }
            args.append(arg)
        return args

    @staticmethod
    def get_command_args(command: Command) -> T.List[dict]:
        args = []
        for ph in command.placeholders:
            arg = {
                "name": ph,
                "type": "str",
                "range": None,
                "default": None,
            }
            args.append(arg)
        return args


def task(
        target=None,
        name: T.Optional[str]=None,
        description: str = "",
        job_type: T.Optional[JobType] = None,
        ):
    if target is None:
        return functools.partial(task, name=name, description=description, job_type=job_type)
    return Task(target, name=name, description=description, job_type=job_type)



class TaskTable(object):
    def __init__(self, table: T.Optional[T.Dict[str, Task]] = None) -> None:
        self.table: T.Dict[str, Task] = table or {}

    def __getitem__(self, key) -> Task:
        return self.table[key]

    def register(self, task: T.Union[Task, T.Callable, str]):
        if not isinstance(task, Task):
            task = Task(task)
        self.table[task.name] = task
