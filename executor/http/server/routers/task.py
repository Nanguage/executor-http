import typing as T
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..config import task_table
from ..instance import engine
from ..utils import ConditionType, ser_job


router = APIRouter(prefix="/task")


class CallRequest(BaseModel):
    task_name: str
    args: T.List[T.Any]
    kwargs: T.Dict[str, T.Any]
    condition: T.Optional[ConditionType] = None


@router.post("/call")
async def call(req: CallRequest):
    try:
        task = task_table[req.task_name]
    except KeyError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Function not registered.")

    condition = None
    if req.condition is not None:
        if req.condition.type == "AfterAnother":
            condition = req.condition.arguments
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported condition type: {req.condition.type}."
            )

    try:
        job = task.create_job(tuple(req.args), req.kwargs, condition)
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Error when create job: {str(e)}",
        )
    await engine.submit(job)
    return ser_job(job)


@router.get("/list_all")
async def get_task_list():
    return [t.to_dict() for t in task_table.table.values()]
