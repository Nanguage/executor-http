from email.policy import default
from fastapi import APIRouter, HTTPException, status

from executor.engine.manager import Jobs
from executor.engine.job import Job

from .. import config
from ..utils import ser_job

jobs = Jobs(config.monitor_cache_path)

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
