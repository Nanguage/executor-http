import typing as T
import os
from os.path import abspath, join
from shutil import rmtree
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import config


router = APIRouter(prefix="/file")


class ListDirRequest(BaseModel):
    path: str


def is_sub_path(parent: Path, sub: Path) -> bool:
    return abspath(sub).startswith(abspath(parent))


def get_path(path_str: str) -> Path:
    working_path = Path(config.working_dir).absolute()
    path = (working_path / path_str).absolute()
    if not is_sub_path(working_path, path):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Requested path can't outside the working dir: {path_str}")
    return path


@router.post("/list_dir")
async def list_dir(req: ListDirRequest):
    path = get_path(req.path)
    if (not path.exists()) or (not path.is_dir()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The dir is not exists.")
    else:
        files = []
        for p in path.glob("*"):
            stat = p.stat()
            f = {
                "name": p.name,
                "isDir": p.is_dir(),
                "modDate": str(datetime.fromtimestamp(stat.st_mtime)),
                "size": stat.st_size,
            }
            files.append(f)
        return files


class DownloadReq(BaseModel):
    path: str


@router.post("/download")
async def download(req: DownloadReq):
    path = get_path(req.path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The file is not exists.")
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The path is not a file.")
    return FileResponse(abspath(path))


@router.post("/upload")
async def upload(path: str, files: T.List[UploadFile] = File(...)):
    for file in files:
        file_path = get_path(join(path, file.filename))
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)


class DeleteReq(BaseModel):
    paths: T.List[str]


@router.post("/delete")
async def delete(req: DeleteReq):
    paths_to_delete: T.List[Path] = []
    for p in req.paths:
        path = get_path(p)
        paths_to_delete.append(path)
    for path in paths_to_delete:
        if path.is_dir():
            rmtree(path)
        else:
            os.remove(path)
