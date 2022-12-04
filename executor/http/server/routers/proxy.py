import re
import functools

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse, RedirectResponse
from starlette.background import BackgroundTask

from executor.engine.job.extend import WebAppJob

from ..utils import get_jobs


router = APIRouter(prefix="/proxy")
jobs = get_jobs()


@functools.lru_cache(maxsize=None)
def get_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url)


def remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


async def _reverse_proxy(job_id: str, request: Request):
    job = jobs.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not exist.",)
    if not isinstance(job, WebAppJob):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not a WebAppJob.",)
    if (job.status != "running") or (job.port is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not running",)
    address = f"http://{job.ip}:{job.port}"
    client = get_client(address)
    path_prefix = f"/proxy/app/{job_id}/"
    path = remove_prefix(request.url.path, path_prefix)
    url = httpx.URL(path=path, query=request.url.query.encode("utf-8"))
    req = client.build_request(
        request.method, url, headers=request.headers.raw,
        content=await request.body()
    )
    count = 5  # max try
    while count - 1 > 0:
        try:
            resp = await client.send(req, stream=True)
            break
        except httpx.ConnectError:
            pass
        count -= 1
    else:
        resp = await client.send(req, stream=True)
    if resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        return RedirectResponse(
            path_prefix+resp.headers['location'], headers=resp.headers)
    headers = req.headers.copy()
    if 'content-length' in headers:
        headers.pop('content-length')
    headers['Set-Cookie'] = f'proxy_job="{job_id}"; Path=/'
    return StreamingResponse(
        resp.aiter_raw(),
        status_code=resp.status_code,
        headers=headers,
        background=BackgroundTask(resp.aclose),
    )


@router.get("/app/{job_id}/{path:path}")
async def proxy_get(job_id: str, request: Request):
    return await _reverse_proxy(job_id, request)


@router.post("/app/{job_id}/{path:path}")
async def proxy_post(job_id: str, request: Request):
    return await _reverse_proxy(job_id, request)


async def root_dispatch(request: Request):
    headers = request.headers
    if 'Cookie' in headers:
        cookie = headers['Cookie']
        if 'proxy_job' in cookie:
            match = re.match('.*proxy_job="(.*?)"', cookie)
            if match is not None:
                job_id = match.groups()[0]
                return await _reverse_proxy(job_id, request)
