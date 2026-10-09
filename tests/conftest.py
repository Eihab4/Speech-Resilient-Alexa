import pytest

from support import start_server


@pytest.fixture
def server(tmp_path):
    processes = []

    def start(path: str = "/mcp", **env: str | None) -> str:
        process, url = start_server(path, MEMORY_DB_PATH=str(tmp_path / "memory.db"), **env)
        processes.append(process)
        return url

    yield start
    for process in processes:
        process.terminate()
        process.wait()
