import typing as T
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from executor.engine.job.utils import InvalidStateError, JobEmitError
from executor.engine.job import Job

from ..instance import engine
from ..config import valid_job_type


router = APIRouter(prefix="/job")


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


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = engine.jobs.get_job_by_id(job_id)
    if job:
        return ser_job(job)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found.")


@router.get("/valid_types")
async def get_valid_job_types():
    return valid_job_type


@router.get("/list_all")
async def get_all_jobs():
    resp = []
    job: Job
    for job in engine.jobs.all_jobs():
        resp.append(ser_job(job))
    return resp


@router.get("/cancel/{job_id}")
async def cancel_job(job_id: str):
    running = engine.jobs.running
    pending = engine.jobs.pending
    if job_id in running:
        job = running[job_id]
        await job.cancel()
        return ser_job(job)
    elif job_id in pending:
        job = pending[job_id]
        await job.cancel()
        return ser_job(job)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="The job is not in running or pending.")


@router.get("/re_run/{job_id}")
async def re_run_job(job_id: str):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
    try:
        await job.rerun()
        return ser_job(job)
    except JobEmitError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=str(e))


@router.get("/result/{job_id}")
async def wait_job_result(job_id: str):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
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


def _read_then_return(job_id: str, fname: str):
    job = engine.jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Job not found")
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
async def get_job_stdout(job_id: str):
    return _read_then_return(job_id, "stdout.txt")


@router.get("/stderr/{job_id}")
async def get_job_stderr(job_id: str):
    return _read_then_return(job_id, "stderr.txt")
