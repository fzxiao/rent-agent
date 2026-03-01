"""Pytest 配置：Mock 模式、TestClient。"""

import os

import pytest

# 确保使用 Mock 模式
os.environ["RENT_AGENT_USE_MOCK"] = "true"


def pytest_sessionstart(session):
    """测试开始前备份旧日志、准备新日志。"""
    from rent_agent import logger
    logger.prepare_log_for_new_run()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from rent_agent.main import app
    return TestClient(app)
