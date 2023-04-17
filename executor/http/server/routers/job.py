import typing as T
import asyncio

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from executor.engine import Engine
from executor.engine.job.utils import InvalidStateError
from executor.engine.job import Job
from executor.engine.job.base import JobStatusType
from executor.engine.manager import JobNotFoundError

from ..utils import ser_job, get_app, CustomFastAPI
from ..utils.auth import get_current_user, check_user_job, user_can_access
from ..user_db.schemas import User


router = APIRouter(prefix="/job")


def get_job(engine: Engine, job_id: str, user: T.Optional[User]) -> Job:
    try:
        job = engine.jobs.get_job_by_id(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found.")
    job = check_user_job(user, job)
    return job


def is_allow_proxy(app: "CustomFastAPI") -> bool:
    return "proxy" in app.config.allowed_routers


@router.get("/status/{job_id}")
async def get_job_status(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    return ser_job(job, is_allow_proxy(app))


@router.get("/list_all")
async def get_all_jobs(
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    resp = []
    job: Job
    all_jobs = app.engine.jobs.all_jobs()
    if user is None:
        jobs = all_jobs
    else:
        jobs = (j for j in all_jobs if user_can_access(user, j))
    for job in jobs:
        resp.append(ser_job(job, is_allow_proxy(app)))
    return resp


@router.get("/cancel/{job_id}")
async def cancel_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    if job.status in ("running", "pending"):
        await job.cancel()
        return ser_job(job, is_allow_proxy(app))
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The job is not in running or pending.")


@router.get("/re_run/{job_id}")
async def re_run_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    try:
        await job.rerun()
        return ser_job(job, is_allow_proxy(app))
    except InvalidStateError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.get("/remove/{job_id}")
async def remove_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    if job.status in ("pending", "running"):
        await job.cancel()
    app.engine.jobs.remove(job)
    return ser_job(job, is_allow_proxy(app))


@router.get("/result/{job_id}")
async def wait_job_result(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    await job.join()
    return {
        'job': ser_job(job, is_allow_proxy(app)),
        'result': job.result(),
    }


class WaitRequest(BaseModel):
    job_id: str
    statuses: T.List[JobStatusType] = ["done", "failed", "cancelled"]
    time_delta: float = 0.1


@router.post("/wait")
async def wait(
        req: WaitRequest,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, req.job_id, user)
    while True:
        if job.status in req.statuses:
            break
        await asyncio.sleep(req.time_delta)
    return ser_job(job, is_allow_proxy(app))


def _read_then_return(job: Job, fname: str):
    try:
        with open(job.cache_dir / fname) as f:
            content = f.read()
        return {'content': content}
    except Exception as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/stdout/{job_id}")
async def get_job_stdout(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    return _read_then_return(job, "stdout.txt")


@router.get("/stderr/{job_id}")
async def get_job_stderr(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user),
        app: "CustomFastAPI" = Depends(get_app)):
    job = get_job(app.engine, job_id, user)
    return _read_then_return(job, "stderr.txt")
