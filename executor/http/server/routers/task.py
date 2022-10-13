import typing as T
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from executor.engine.job import Job, LocalJob, ThreadJob, ProcessJob

from ..config import task_table, valid_job_type
from ..instance import engine


router = APIRouter(prefix="/task")


class CallRequest(BaseModel):
    task_name: str
    args: T.List
    kwargs: T.Dict[str, T.Any]
    job_type: T.Literal["local", "thread", "process"]


@router.post("/call")
async def call(req: CallRequest):
    try:
        task = task_table[req.task_name]
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Function not registered.")

    job_cls: T.Type["Job"]

    if req.job_type not in valid_job_type:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Not valid job type: {req.job_type}")

    if req.job_type == "local":
        job_cls = LocalJob
    elif req.job_type == "thread":
        job_cls = ThreadJob
    else:
        job_cls = ProcessJob

    job = job_cls(
        task.func, tuple(req.args), req.kwargs,
        callback=None,
        error_callback=None,
        name=task.name)
    await engine.submit(job)
    return job.to_dict()


@router.get("/list_all")
async def get_task_list():
    return [t.to_dict() for t in task_table.table.values()]
