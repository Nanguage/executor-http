import typing as T
from copy import copy
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

from pydantic import BaseModel
from fastapi import FastAPI, Request

from executor.engine.job import Job, LocalJob, ThreadJob, ProcessJob
from executor.engine.job.extend import SubprocessJob, WebappJob
from executor.engine.manager import Jobs

if T.TYPE_CHECKING:
    from executor.engine import Engine
    from ..config import ServerSetting
    from ..task import TaskTable
    from sqlalchemy.ext.asyncio import AsyncEngine


class CustomFastAPI(FastAPI):
    config: "ServerSetting"
    task_table: "TaskTable"
    engine: "Engine"
    db_engine: T.Optional["AsyncEngine"]
    include_proxy_router: T.Callable


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


def ser_job(job: Job, allow_proxy: bool) -> dict:
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
    if allow_proxy:
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


def get_app(request: Request) -> CustomFastAPI:
    return request.app


def get_jobs(app: CustomFastAPI) -> Jobs:
    if app.config.monitor_mode:
        if app.config.monitor_cache_path is not None:
            cache_path = Path(app.config.monitor_cache_path)
            jobs = Jobs(cache_path / "jobs")
        else:
            raise ValueError(
                "Monitor cache path is not provided, please set it in config.")
    else:
        jobs = app.engine.jobs
    return jobs
