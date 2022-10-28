import typing as T
from datetime import datetime

from executor.engine.job import Job


def format_datetime(d: T.Optional[datetime]):
    if d is None:
        return None
    else:
        return str(d)


def ser_job(job: Job) -> dict:
    d = job.to_dict()
    for k, v in d.items():
        if k.endswith("_time"):
            d[k] = format_datetime(v)
    return d

