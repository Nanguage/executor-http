import typing as T
import os
from pathlib import Path
import shutil

from fastapi.testclient import TestClient


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
    resp = client.post(
        "/file/download",
        json={"path": "not_exist"},
        headers=headers
    )
    assert resp.status_code == 404
    test_dir = Path("test_dir/")
    test_dir_path = base_path / test_dir
    test_dir_path.mkdir(exist_ok=True)
    resp = client.post(
        "/file/download",
        json={"path": str(test_dir)},
        headers=headers
    )
    assert resp.status_code == 400


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
    # test the error when the destination is not a directory
    resp = client.post(
        "/file/move",
        json={
            "paths": files_for_move,
            "destination": str(dest_dir_path / "a.txt"),
        },
        headers=headers,
    )
    assert resp.status_code == 400
    # test the normal case
    resp = client.post(
        "/file/move",
        json={
            "paths": files_for_move,
            "destination": str(dest_dir),
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert all([
        (Path(dest_dir_path) / f.name).exists()
        for f in files_path_for_move
    ])
    assert all([(not Path(f).exists()) for f in files_path_for_move])
    shutil.rmtree(dest_dir_path)
