import re
import sys
import traceback
import typing as T
from copy import copy
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

from pydantic import BaseModel

from executor.engine.job import Job, LocalJob, ThreadJob, ProcessJob
from executor.engine.job.extend import SubprocessJob, WebappJob
from executor.engine.manager import Jobs

from .. import config


class ConditionType(BaseModel):
    type: str
    arguments: dict


def format_datetime(d: T.Optional[datetime]):
    if d is None:
        return None
    else:
        return str(d)


JobType = T.Literal["process", "thread", "local", "subprocess", "webapp"]

jobtype_classes: T.Dict[JobType, T.Type[Job]] = {
    "process": ProcessJob,
    "thread": ThreadJob,
    "local": LocalJob,
    "subprocess": SubprocessJob,
    "webapp": WebappJob,
}

_class_name_to_jobtype = {v.__name__: k for k, v in jobtype_classes.items()}


def job_to_jobtype(job: Job) -> JobType:
    type_name = type(job).__name__
    if type_name == "_WebappJob":
        return "webapp"
    elif type_name == "_SubprocessJob":
        return "subprocess"
    return _class_name_to_jobtype[type_name]


def ser_job(job: Job) -> dict:
    """Convert job to a JSON-able dict."""
    if job.condition is not None:
        cls_name = job.condition.__class__.__name__
        cond = ConditionType(
            type=cls_name,
            arguments=asdict(job.condition)
        )
        cond_dict = cond.dict()
    else:
        cond_dict = None

    attrs = copy(job.attrs)
    if 'proxy' in config.allowed_routers:
        if 'address' in job.attrs:
            attrs.pop('address')

    if 'user' in job.attrs:
        attrs.pop('user')

    return {
        'id': job.id,
        'name': job.name,
        'args': job.args,
        'kwargs': job.kwargs,
        'condition': cond_dict,
        'status': job.status,
        'job_type': job_to_jobtype(job),
        'created_time': format_datetime(job.created_time),
        'submit_time': format_datetime(job.submit_time),
        'stoped_time': format_datetime(job.stoped_time),
        'attrs': attrs,
    }


class Command(object):
    def __init__(self, template: str):
        self.template = template
        self.placeholders = [
            p.strip("{}") for p in
            re.findall(r"\{.*?\}", self.template)
        ]
        self.name = template.split()[0]

    def check_placeholder(self, arg_names: T.List[str]):
        for arg in arg_names:
            if arg not in self.placeholders:
                raise ValueError(
                    f"The argument {arg} is not in command templates.")

    def format(self, vals: dict):
        for ph in self.placeholders:
            if ph not in vals:
                raise ValueError(
                    f"The value of placeholder {ph} is not provided.")
        cmd = self.template.format(**vals)
        return cmd


def print_error(err):
    traceback.print_exc(file=sys.stderr)
    print(err, file=sys.stderr)


def get_jobs() -> Jobs:
    if config.monitor_mode:
        if config.monitor_cache_path is not None:
            cache_path = Path(config.monitor_cache_path)
            jobs = Jobs(cache_path / "jobs")
        else:
            raise ValueError(
                "Monitor cache path is not provided, please set it in config.")
    else:
        from ..instance import engine
        jobs = engine.jobs
    return jobs


def reload_routers():
    """Reload router modules
    for switch user-mode / reload engine."""
    import importlib
    from .. import auth
    from ..routers import file, job, monitor, proxy, task
    modules = [auth, file, job, monitor, proxy, task]
    for mod in modules:
        importlib.reload(mod)
