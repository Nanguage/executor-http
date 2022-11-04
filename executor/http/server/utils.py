import typing as T
from datetime import datetime

from pydantic import BaseModel

from executor.engine.job import Job
from executor.engine.job.condition import (
    Condition,
    AfterAnother, AfterOthers, AfterTimepoint, AllSatisfied, AnySatisfied,
)


class ConditionType(BaseModel):
    type: str
    arguments: T.Union[
        AfterAnother, AfterOthers, AfterTimepoint, AllSatisfied, AnySatisfied,
    ]


def format_datetime(d: T.Optional[datetime]):
    if d is None:
        return None
    else:
        return str(d)


def ser_job(job: Job) -> dict:
    """Convert job to a JSON-able dict."""
    if job.condition is not None:
        cls_name = job.condition.__class__.__name__
        cond = ConditionType(type=cls_name, arguments=job.condition)
        cond_dict = cond.dict()
    else:
        cond_dict = None

    return {
        'id': job.id,
        'name': job.name,
        'args': job.args,
        'kwargs': job.kwargs,
        'condition': cond_dict,
        'status': job.status,
        'job_type': job.job_type,
        'created_time': format_datetime(job.created_time),
        'submit_time': format_datetime(job.submit_time),
        'stoped_time': format_datetime(job.stoped_time),
    }


