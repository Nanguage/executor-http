import os
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from executor.http.server.app import create_app
from executor.http.server import config


@pytest.fixture
def client() -> TestClient:
    config.allowed_routers = ["file"]
    app = create_app()
    client = TestClient(app)
    return client


def test_list_dir(client: TestClient):
    resp = client.post(
        "/file/list_dir",
        json={
            "path": ""
        }
    )
    assert resp.status_code == 200
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "not_exists"
        }
    )
    assert resp.status_code == 404
    resp = client.post(
        "/file/list_dir",
        json={
            "path": "../../"
        }
    )
    assert resp.status_code == 403


def test_download_file(client: TestClient):
    test_file = "for_download.txt"
    with open(test_file, 'w') as f:
        f.write("123")
    resp = client.post("/file/download", json={"path": test_file})
    assert resp.status_code == 200
    os.remove(test_file)    


def test_upload_file(client: TestClient):
    test_file = "for_upload.txt"
    with open(test_file, 'w') as f:
        f.write("123")
    target_path = Path("test_upload/")
    target_path.mkdir(exist_ok=True)
    with open(test_file, 'rb') as f:
        files = {'files': f}
        resp = client.post(
            f"/file/upload?path={target_path}",
            files=files,
            )
        assert resp.status_code == 200
    with open(target_path/test_file, 'r') as f:
        assert f.read() == "123"
    shutil.rmtree(target_path)
    os.remove(test_file)


def test_delete_files(client: TestClient):
    files_for_delete = ["a.txt", "b.txt"]
    for fname in files_for_delete:
        with open(fname, 'w') as f:
            f.write("111")
    resp = client.post(
        "/file/delete", json={"paths": files_for_delete})
    assert resp.status_code == 200
    assert all([not Path(f).exists() for f in files_for_delete])
    dirs_for_delete = ["test_dir1/", "test_dir2/"]
    for d in dirs_for_delete:
        os.mkdir(d)
        with open(d+"/a", 'w') as f:
            f.write("1")
    resp = client.post(
        "/file/delete", json={"paths": dirs_for_delete})
    assert resp.status_code == 200
    assert all([not Path(f).exists() for f in dirs_for_delete])


def test_move_files(client: TestClient):
    files_for_move = ["a.txt", "b.txt"]
    for fname in files_for_move:
        with open(fname, 'w') as f:
            f.write("111")
    dest_dir = "test_dest_dir1/"
    os.mkdir(dest_dir)
    resp = client.post(
        "/file/move",
        json={
            "paths": files_for_move,
            "destination": dest_dir,
        }
    )
    assert resp.status_code == 200
    assert all([(Path(dest_dir) / f).exists() for f in files_for_move])
    assert all([(not Path(f).exists()) for f in files_for_move])
    shutil.rmtree(dest_dir)
