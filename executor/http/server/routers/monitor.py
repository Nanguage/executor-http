import typing as T
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Depends

from ..utils import ser_job, get_jobs, get_app, CustomFastAPI


router = APIRouter(prefix="/monitor")


@router.get("/list_all")
async def get_all_jobs_from_cache(
        app: "CustomFastAPI" = Depends(get_app)
        ):
    jobs = get_jobs(app)
    jobs.update_from_cache()
    resp = []
    allow_proxy = 'proxy' in app.config.allowed_routers
    for job in jobs.all_jobs():
        resp.append(ser_job(job, allow_proxy))
    return resp


def _read_then_return(
        job_id: str, log_file: str,
        monitor_cache_path: T.Union[str, Path]):
    cache_path = Path(monitor_cache_path)
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
async def get_job_stdout(
        job_id: str,
        app: "CustomFastAPI" = Depends(get_app)):
    cache_path = app.config.monitor_cache_path
    assert cache_path is not None
    return _read_then_return(
        job_id, "stdout.txt", cache_path)


@router.get("/stderr/{job_id}")
async def get_job_stderr(
        job_id: str,
        app: "CustomFastAPI" = Depends(get_app)):
    cache_path = app.config.monitor_cache_path
    assert cache_path is not None
    return _read_then_return(
        job_id, "stderr.txt", cache_path)
