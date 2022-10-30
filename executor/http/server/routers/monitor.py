import typing as T
from pathlib import Path
from fastapi import APIRouter, HTTPException, status

from executor.engine.manager import Jobs
from executor.engine.job import Job

from .. import config
from ..utils import ser_job

if config.monitor_cache_path is not None:
    cache_path = Path(config.monitor_cache_path)
    jobs = Jobs(cache_path / "jobs")
else:
    raise ValueError("Monitor cache path is not provided, please set it in config.")

router = APIRouter(prefix="/monitor")


@router.get("/list_all")
async def get_all_jobs_from_cache():
    try:
        jobs.update_from_cache()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e))
    resp = []
    job: Job
    for job in jobs.all_jobs():
        resp.append(ser_job(job))
    return resp


def _read_then_return(job_id: str, log_file: str):
    if config.monitor_cache_path is not None:
        cache_path = Path(config.monitor_cache_path)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Monitor cache path is not provided, please set it in config."
        )
    job_cache_dir = cache_path / job_id
    try:
        with open(job_cache_dir / log_file) as f:
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
