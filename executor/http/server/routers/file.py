from os.path import abspath
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from .. import config


router = APIRouter(prefix="/file")


class ListDirRequest(BaseModel):
    path: str


def is_sub_path(parent: Path, sub: Path) -> bool:
    return abspath(sub).startswith(abspath(parent))


@router.post("/list_dir")
async def list_dir(req: ListDirRequest):
    working_path = Path(config.working_dir).absolute()
    path = (working_path / req.path).absolute()
    if not is_sub_path(working_path, path):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Requested path can't outside the working dir")
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
