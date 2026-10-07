import pytest

from support import start_server


@pytest.fixture
def server():
    processes = []

    def start(path: str = "/mcp", **env: str) -> str:
        process, url = start_server(path, **env)
        processes.append(process)
        return url

    yield start
    for process in processes:
        process.terminate()
        process.wait()
