import typing as T
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from executor.engine.job.condition import AfterAnother

from ..config import task_table, redirect_job_stream
from ..instance import engine
from ..utils import ConditionType, ser_job
from ..auth import get_current_user
from ..user_db.schemas import User


router = APIRouter(prefix="/task")


class CallRequest(BaseModel):
    task_name: str
    args: T.List[T.Any]
    kwargs: T.Dict[str, T.Any]
    condition: T.Optional[ConditionType] = None


@router.post("/call")
async def call(
        req: CallRequest,
        user: T.Optional[User] = Depends(get_current_user)):
    try:
        task = task_table[req.task_name]
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Function not registered.")

    condition = None
    if req.condition is not None:
        if req.condition.type == "AfterAnother":
            condition = AfterAnother(**req.condition.arguments)
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported condition type: {req.condition.type}."
            )
    try:
        job = task.create_job(
            tuple(req.args), req.kwargs, condition=condition)
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Error when create job: {str(e)}",
        )
    if user is not None:
        job.attrs['user'] = user
    if redirect_job_stream:
        job.redirect_out_err = True
    await engine.submit_async(job)
    return ser_job(job)


@router.get("/list_all")
async def get_task_list(user: T.Optional[User] = Depends(get_current_user)):
    task_list = [
        task_table.task_to_dict(t)
        for t in task_table.table.values()
    ]
    return task_list
