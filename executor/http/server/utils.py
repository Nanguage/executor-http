import re
import sys
import traceback
import typing as T
from datetime import datetime

from pydantic import BaseModel

from executor.engine.job import Job, LocalJob, ThreadJob, ProcessJob
from executor.engine.job.extend import SubprocessJob, WebAppJob
from executor.engine.job.condition import (
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


JobType = T.Literal["process", "thread", "local", "subprocess", "webapp"]

jobtype_classes: T.Dict[JobType, T.Type[Job]] = {
    "process": ProcessJob,
    "thread": ThreadJob,
    "local": LocalJob,
    "subprocess": SubprocessJob,
    "webapp": WebAppJob,
}


def job_to_jobtype(job: Job) -> JobType:
    for job_type, cls in jobtype_classes.items():
        if isinstance(job, cls):
            return job_type
    return "process"


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
        'job_type': job_to_jobtype(job),
        'created_time': format_datetime(job.created_time),
        'submit_time': format_datetime(job.submit_time),
        'stoped_time': format_datetime(job.stoped_time),
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