import typing as T
import os
import shutil
from os.path import abspath, join
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, File, UploadFile, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..utils import auth, get_app, CustomFastAPI

from ..user_db.schemas import User


router = APIRouter(prefix="/file")


class ListDirRequest(BaseModel):
    path: str


def is_sub_path(parent: Path, sub: Path) -> bool:
    return abspath(sub).startswith(abspath(parent))


def get_path(root_path: Path, path_str: str) -> Path:
    path = (root_path / path_str).absolute()
    if not is_sub_path(root_path, path):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Requested path can't outside the working dir: {path_str}")
    return path


def get_user_path(
        user: T.Optional[User] = Depends(auth.get_current_user),
        app: "CustomFastAPI" = Depends(get_app)) -> Path:
    working_path = Path(app.config.working_dir).absolute()
    if user is None:
        return working_path
    else:
        path = working_path / user.username
        if not path.exists():
            path.mkdir(exist_ok=True)
        return path


@router.post("/list_dir")
async def list_dir(
        req: ListDirRequest,
        user_path: Path = Depends(get_user_path)):
    path = get_path(user_path, req.path)
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
async def download(
        req: DownloadReq,
        user_path: Path = Depends(get_user_path)):
    path = get_path(user_path, req.path)
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
async def upload(
        path: str,
        files: T.List[UploadFile] = File(...),
        user_path: Path = Depends(get_user_path)):
    for file in files:
        assert file.filename is not None
        file_path = get_path(user_path, join(path, file.filename))
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)


class DeleteReq(BaseModel):
    paths: T.List[str]


@router.post("/delete")
async def delete(
        req: DeleteReq,
        user_path: Path = Depends(get_user_path)):
    paths_to_delete: T.List[Path] = []
    for p in req.paths:
        path = get_path(user_path, p)
        paths_to_delete.append(path)
    for path in paths_to_delete:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            os.remove(path)


class MoveReq(BaseModel):
    paths: T.List[str]
    destination: str


@router.post("/move")
async def move(
        req: MoveReq,
        user_path: Path = Depends(get_user_path)):
    path_dest = get_path(user_path, req.destination)
    if not path_dest.is_dir():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"The move destination is not a dir: {path_dest}")
    paths_to_move: T.List[Path] = []
    for p in req.paths:
        path = get_path(user_path, p)
        paths_to_move.append(path)
    for path in paths_to_move:
        shutil.move(
            str(path),
            str(path_dest / path.name))
