"""pytest 配置与 fixtures"""
import pytest
from unittest.mock import AsyncMock, patch

from src.session_manager import SessionManager


@pytest.fixture
def session_manager():
    return SessionManager()
