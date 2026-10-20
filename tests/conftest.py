import pytest

from support import RunNow, start_server


@pytest.fixture
def history_in_line(monkeypatch):
    monkeypatch.setattr("memory.history.Thread", RunNow)


@pytest.fixture
def server(tmp_path):
    processes = []

    def start(path: str = "/mcp", **env: str | None) -> str:
        process, url = start_server(
            path,
            MEMORY_DB_PATH=str(tmp_path / "memory.db"),
            LLM_PROVIDER=env.pop("LLM_PROVIDER", None) or "mock",
            TELEGRAM_BOT_TOKEN=env.pop("TELEGRAM_BOT_TOKEN", ""),
            LOCATION_ENABLED=env.pop("LOCATION_ENABLED", "false"),
            **env,
        )
        processes.append(process)
        return url

    yield start
    for process in processes:
        process.terminate()
        process.wait()
