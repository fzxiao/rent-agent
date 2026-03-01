"""pytest 配置与 fixtures"""
import subprocess
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def mock_api_url() -> str:
    return "http://localhost:8081"


@pytest.fixture(scope="session")
def mock_llm_ip() -> str:
    return "127.0.0.1"


@pytest.fixture(scope="session")
def agent_url() -> str:
    return "http://localhost:8191/api/v1/chat"


def _wait_for_url(url: str, timeout: float = 5.0) -> bool:
    """等待服务就绪"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url.replace("/api/v1/chat", "/health"), timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


@pytest.fixture(scope="session")
def mock_rental_api_process():
    """启动 Mock 租房 API（session 级）"""
    proc = subprocess.Popen(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "uvicorn", "mock_rental_api:app", "--host", "0.0.0.0", "--port", "8081"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    try:
        r = httpx.get("http://localhost:8081/api/landmarks", timeout=2.0)
        if r.status_code != 200:
            raise RuntimeError("Mock API 未就绪")
    except Exception as e:
        proc.kill()
        raise pytest.skip(f"Mock API 启动失败: {e}") from e
    yield proc
    proc.terminate()
    proc.wait(timeout=3)
