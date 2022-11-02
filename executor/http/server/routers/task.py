import sys
import typing as T
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from executor.engine.job import Job, LocalJob, ThreadJob, ProcessJob

from ..config import task_table, valid_job_types
from ..instance import engine
from ..utils import ConditionType, ser_job


router = APIRouter(prefix="/task")


class CallRequest(BaseModel):
    task_name: str
    args: T.List[T.Any]
    kwargs: T.Dict[str, T.Any]
    job_type: T.Literal["local", "thread", "process"]
    condition: T.Optional[ConditionType] = None


@router.post("/call")
async def call(req: CallRequest):
    try:
        task = task_table[req.task_name]
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Function not registered.")

    job_cls: T.Type["Job"]

    if req.job_type not in valid_job_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Not valid job type: {req.job_type}")

    if req.job_type == "local":
        job_cls = LocalJob
    elif req.job_type == "thread":
        job_cls = ThreadJob
    else:
        job_cls = ProcessJob

    condition = None
    if req.condition is not None:
        if req.condition.type == "AfterAnother":
            condition = req.condition.arguments
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported condition type: {req.condition.type}."
            )

    def print_error(err):
        print(err, file=sys.stderr)

    job = job_cls(
        task.func, tuple(req.args), req.kwargs,
        callback=None,
        error_callback=print_error,
        name=task.name,
        redirect_out_err=True,
        condition=condition,
    )
    await engine.submit(job)
    return ser_job(job)


@router.get("/list_all")
async def get_task_list():
    return [t.to_dict() for t in task_table.table.values()]
