from fastapi import APIRouter, HTTPException, status

from executor.engine.job.utils import InvalidStateError, JobEmitError

from ..instance import engine
from ..config import valid_job_type


router = APIRouter(prefix="/job")


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = engine.jobs.get_job_by_id(job_id)
    if job:
        return job.to_dict()
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
    for job in engine.jobs.all_jobs():
        resp.append(job.to_dict())
    return resp


@router.get("/cancel/{job_id}")
async def cancel_job(job_id: str):
    running = engine.jobs.running
    pending = engine.jobs.pending
    if job_id in running:
        job = running[job_id]
        await job.cancel()
        return job.to_dict()
    elif job_id in pending:
        job = pending[job_id]
        await job.cancel()
        return job.to_dict()
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
        return job.to_dict()
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
            'job': job.to_dict(),
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
