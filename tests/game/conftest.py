import time
import uuid

import pytest
import requests

from clients.game_client import GameClient
from config.settings import settings


@pytest.fixture(scope="session", autouse=True)
def ensure_game_server():
    """确认服务器「就绪」，而不只是「能响应」。

    只 ping /docs 是不够的：服务器 --reload 重启期间会短暂处于
    「路由只注册了一半」的状态（register 有、login 没有），
    那时用例会收到一堆莫名其妙的 404。这里等它真正就绪再开跑。
    """
    url = f"{settings.game_api_base_url}/openapi.json"
    last = "未知错误"
    for _ in range(10):                                   # 最多等 5 秒
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200 and "/api/login" in resp.json().get("paths", {}):
                return
            last = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last = exc.__class__.__name__
        time.sleep(0.5)
    pytest.skip(
        f"游戏服务器未就绪（{last}）：请先在另一个终端执行 "
        "uvicorn game_server:app --reload --port 8000"
    )


@pytest.fixture
def game_client():
    """每个用例分配一个全新账号——不依赖任何历史状态，测试可重复执行"""
    client = GameClient()
    username = "t" + uuid.uuid4().hex[:8]        # 唯一用户名（9 位，符合 3~12 规则）
    reg = client.register(username, "abc123")
    assert reg.status_code == 201, f"测试账号注册失败: {reg.text}"
    login = client.login(username, "abc123")
    assert login.status_code == 200, f"测试账号登录失败: {login.text}"
    return client
@pytest.fixture
def unique_username() -> str:
    """每次调用生成一个唯一的合法用户名（9 位）"""
    return "t" + uuid.uuid4().hex[:8]
