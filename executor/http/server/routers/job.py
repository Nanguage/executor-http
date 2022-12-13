import typing as T
import asyncio
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from executor.engine.job.utils import InvalidStateError, JobEmitError
from executor.engine.job import Job
from executor.engine.job.base import JobStatusType

from ..utils import ser_job
from ..instance import engine
from ..auth import get_current_user
from ..user_db.schemas import User


router = APIRouter(prefix="/job")


def check_user_job(user: T.Optional[User], job: Job) -> Job:
    if user is None:
        return job
    else:
        job_user = job.attrs.get("user")
        if user.username == job_user:
            return job
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Can't access to the job."
            )


@router.get("/status/{job_id}")
async def get_job_status(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    job = engine.jobs.get_job_by_id(job_id)
    if job is not None:
        job = check_user_job(user, job)
        return ser_job(job)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found.")


@router.get("/list_all")
async def get_all_jobs(user: T.Optional[User] = Depends(get_current_user)):
    resp = []
    job: Job
    all_jobs = engine.jobs.all_jobs()
    if user is None:
        jobs = all_jobs
    else:
        jobs = (j for j in all_jobs if j.attrs.get('user') == user.username)
    for job in jobs:
        resp.append(ser_job(job))
    return resp


@router.get("/cancel/{job_id}")
async def cancel_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    running = engine.jobs.running
    pending = engine.jobs.pending
    if job_id in running:
        job = running[job_id]
        job = check_user_job(user, job)
        await job.cancel()
        return ser_job(job)
    elif job_id in pending:
        job = pending[job_id]
        job = check_user_job(user, job)
        await job.cancel()
        return ser_job(job)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The job is not in running or pending.")


@router.get("/re_run/{job_id}")
async def re_run_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    job = check_user_job(user, job)
    try:
        await job.rerun()
        return ser_job(job)
    except JobEmitError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.get("/remove/{job_id}")
async def remove_job(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    job = check_user_job(user, job)
    await engine.remove(job)
    return ser_job(job)


@router.get("/result/{job_id}")
async def wait_job_result(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    job = check_user_job(user, job)
    try:
        await job.join()
        return {
            'job': ser_job(job),
            'result': job.result(),
        }
    except InvalidStateError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job can not fetch result",
        )


class WaitRequest(BaseModel):
    job_id: str
    status: JobStatusType
    time_delta: float = 0.1


@router.post("/wait")
async def wait(
        req: WaitRequest,
        user: T.Optional[User] = Depends(get_current_user)):
    job = engine.jobs.get_job_by_id(req.job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    job = check_user_job(user, job)
    while True:
        if job.status == req.status:
            break
        await asyncio.sleep(req.time_delta)
    return ser_job(job)


def _read_then_return(job_id: str, fname: str, user: T.Optional[User]):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    job = check_user_job(user, job)
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
        user: T.Optional[User] = Depends(get_current_user)):
    return _read_then_return(job_id, "stdout.txt", user)


@router.get("/stderr/{job_id}")
async def get_job_stderr(
        job_id: str,
        user: T.Optional[User] = Depends(get_current_user)):
    return _read_then_return(job_id, "stderr.txt", user)
