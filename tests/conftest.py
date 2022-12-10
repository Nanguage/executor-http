import shutil
import os.path


def pytest_sessionfinish(session, exitstatus):
    # clear root user dir
    root_user_path = "root/"
    if os.path.exists(root_user_path):
        shutil.rmtree(root_user_path)
