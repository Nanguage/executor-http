import typing as T
import os
from pathlib import Path
import shutil
import importlib

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config
from executor.http.server import auth
from executor.http.server.routers import file


@pytest.fixture(params=["free", "hub"])
def client(request) -> TestClient:
    mode = request.param
    if mode == "free":
        config.user_mode = "free"
        config.allowed_routers = ["file"]
        auth.reload()
    else:
        config.allowed_routers = ["file", "user"]
        config.user_mode = "hub"
        config.root_password = "123"
        auth.reload()
    app = create_app()
    app.user_mode = mode
    client = TestClient(app)
    return client


@pytest.fixture
def headers(client: TestClient) -> T.Optional[dict]:
    if client.app.user_mode == "free":
        return None
    else:
        resp = client.post("/user/login", data={
            "username": "root",
            "password": "123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        token = resp.json()["access_token"]
        res = {
            "Authorization": f"Bearer {token}", 
        }
        return res


@pytest.fixture
def base_path(client: TestClient) -> Path:
    if client.app.user_mode == "free":
        return Path(".")
    else:
        return Path("root/")


def test_list_dir(client: TestClient, headers: T.Optional[dict]):
    resp = client.post(
        "/file/list_dir",
        json={
            "path": ""
        },
        headers=headers
    )
    assert resp.status_code == 200
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "not_exists"
        },
        headers=headers
    )
    assert resp.status_code == 404
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "../../"
        },
        headers=headers
    )
    assert resp.status_code == 403


def test_download_file(
        client: TestClient,
        headers: T.Optional[dict],
        base_path: Path):
    test_file = Path("for_download.txt")
    test_file_path = base_path / test_file
    with open(test_file_path, 'w') as f:
        f.write("123")
    resp = client.post(
        "/file/download",
        json={"path": str(test_file)},
        headers=headers
    )
    assert resp.status_code == 200
    os.remove(test_file_path)    


def test_upload_file(
        client: TestClient,
        headers: T.Optional[dict],
        base_path: Path):
    test_file = Path("for_upload.txt")
    test_file_path = base_path / test_file
    with open(test_file_path, 'w') as f:
        f.write("123")
    target_dir = Path("test_upload/")
    target_dir_path = base_path / target_dir
    target_dir_path.mkdir(exist_ok=True)
    with open(test_file_path, 'rb') as f:
        files = {'files': f}
        resp = client.post(
            f"/file/upload?path={target_dir}",
            files=files,
            headers=headers,
            )
        assert resp.status_code == 200
    with open(target_dir_path/test_file, 'r') as f:
        assert f.read() == "123"
    shutil.rmtree(target_dir_path)
    os.remove(test_file_path)


def test_delete_files(
        client: TestClient, headers: T.Optional[dict],
        base_path: Path):
    files_for_delete = ["a.txt", "b.txt"]
    files_paths_for_delete = [base_path / f for f in files_for_delete]
    for fname in files_paths_for_delete:
        with open(fname, 'w') as f:
            f.write("111")
    resp = client.post(
        "/file/delete",
        json={"paths": files_for_delete},
        headers=headers
    )
    assert resp.status_code == 200
    assert all([not Path(f).exists() for f in files_paths_for_delete])
    dirs_for_delete = ["test_dir1/", "test_dir2/"]
    dirs_path_for_delete = [base_path / p for p in dirs_for_delete]
    for d in dirs_path_for_delete:
        os.mkdir(d)
        with open(d / "a", 'w') as f:
            f.write("1")
    resp = client.post(
        "/file/delete",
        json={"paths": dirs_for_delete},
        headers=headers
    )
    assert resp.status_code == 200
    assert all([not Path(f).exists() for f in dirs_path_for_delete])


def test_move_files(
        client: TestClient, headers: T.Optional[dict],
        base_path: Path):
    files_for_move = ["a.txt", "b.txt"]
    files_path_for_move = [base_path / f for f in files_for_move]
    for fname in files_path_for_move:
        with open(fname, 'w') as f:
            f.write("111")
    dest_dir = "test_dest_dir1/"
    dest_dir_path = base_path / dest_dir
    os.mkdir(dest_dir_path)
    resp = client.post(
        "/file/move",
        json={
            "paths": files_for_move,
            "destination": str(dest_dir),
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert all([(Path(dest_dir_path) / f.name).exists() for f in files_path_for_move])
    assert all([(not Path(f).exists()) for f in files_path_for_move])
    shutil.rmtree(dest_dir_path)
