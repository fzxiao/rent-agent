"""租房 API 客户端单元测试（依赖 Mock API）"""
import pytest
import httpx

from agent.rental_client import RentalAPIClient


@pytest.fixture
def client() -> RentalAPIClient:
    return RentalAPIClient(base_url="http://localhost:8081", user_id="test_user")


def _mock_running() -> bool:
    try:
        r = httpx.get("http://localhost:8081/api/landmarks", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _mock_running(), reason="Mock API 未运行，请先执行: python mock_rental_api.py")
def test_init(client: RentalAPIClient) -> None:
    r = client.init()
    assert r.get("code") == 0
    assert "success" in r.get("message", "")


@pytest.mark.skipif(not _mock_running(), reason="Mock API 未运行")
def test_get_houses_by_platform_empty(client: RentalAPIClient) -> None:
    client.init()
    r = client.get_houses_by_platform(
        district="东城",
        max_price=5000,
        bedrooms="2",
        decoration="精装",
        max_subway_dist=500,
    )
    data = r.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    assert len(items) == 0


@pytest.mark.skipif(not _mock_running(), reason="Mock API 未运行")
def test_get_houses_by_platform_xicheng(client: RentalAPIClient) -> None:
    client.init()
    r = client.get_houses_by_platform(
        district="西城",
        bedrooms="1",
        max_subway_dist=1000,
        sort_by="subway",
        sort_order="asc",
    )
    data = r.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    assert len(items) >= 1
    assert items[0].get("house_id") == "HF_13"


@pytest.mark.skipif(not _mock_running(), reason="Mock API 未运行")
def test_get_houses_by_platform_haidian(client: RentalAPIClient) -> None:
    client.init()
    r = client.get_houses_by_platform(
        district="海淀",
        bedrooms="2",
        max_subway_dist=800,
        sort_by="subway",
        sort_order="asc",
    )
    data = r.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    assert len(items) >= 5
    ids = [x.get("house_id") for x in items]
    assert "HF_906" in ids
    assert "HF_1586" in ids
