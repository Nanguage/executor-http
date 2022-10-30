import typing as T
from datetime import datetime

from executor.engine.job import Job
from executor.engine.job.condition import Condition, Combination


def format_datetime(d: T.Optional[datetime]):
    if d is None:
        return None
    else:
        return str(d)


def ser_job(job: Job) -> dict:
    """Convert job to a JSON-able dict."""
    if job.condition is not None:
        cond = ser_condition(job.condition)
    else:
        cond = None

    return {
        'id': job.id,
        'name': job.name,
        'args': job.args,
        'kwargs': job.kwargs,
        'condition': cond,
        'status': job.status,
        'job_type': job.job_type,
        'check_time': datetime.now(),
        'created_time': format_datetime(job.created_time),
        'submit_time': format_datetime(job.submit_time),
        'stoped_time': format_datetime(job.stoped_time),
    }


def ser_condition(condition: Condition) -> dict:
    if isinstance(condition, Combination):
        return {
            'type': condition.__class__.__name__,
            'arguments': {
                'conditions': [
                    ser_condition(c) for c in condition.conditions
                ]
            }
        }
    else:
        return {
            'type': condition.__class__.__name__,
            'arguments': {
                a: getattr(condition, a)
                for a in condition.get_attrs_for_init()
            }
        }

