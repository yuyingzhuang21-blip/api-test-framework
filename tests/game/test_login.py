import pytest

from clients.game_client import GameClient

pytestmark = [pytest.mark.game, pytest.mark.regression]


@pytest.mark.smoke
def test_register_success(unique_username):
    resp = GameClient().register(unique_username, "abc123")
    assert resp.status_code == 201
    assert resp.json()["data"]["gems"] == 16000


def test_register_duplicate_username(unique_username):
    client = GameClient()
    assert client.register(unique_username, "abc123").status_code == 201
    resp = client.register(unique_username, "abc123")
    assert resp.status_code == 400
    assert resp.json()["code"] == 4010


@pytest.mark.parametrize("bad_name", ["ab", "x" * 13])
def test_register_invalid_username_length(bad_name):
    resp = GameClient().register(bad_name, "abc123")
    assert resp.status_code == 400
    assert resp.json()["code"] == 4011


@pytest.mark.parametrize("short_pwd", ["", "a", "12345"])
def test_register_password_too_short(unique_username, short_pwd):
    resp = GameClient().register(unique_username, short_pwd)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4012


def test_login_wrong_password(unique_username):
    client = GameClient()
    client.register(unique_username, "abc123")
    resp = client.login(unique_username, "wrong123")
    assert resp.status_code == 401
    assert resp.json()["code"] == 4001


def test_login_unknown_user():
    resp = GameClient().login("nobody_here", "abc123")
    assert resp.status_code == 401
    assert resp.json()["code"] == 4001


def test_login_empty_username():
    resp = GameClient().login("", "abc123")
    assert resp.status_code == 400
    assert resp.json()["code"] == 4002


def test_relogin_invalidates_old_token(unique_username):
    """重复登录后旧 token 应失效——游戏里对应「另一台设备顶号」"""
    first = GameClient()
    first.register(unique_username, "abc123")
    assert first.login(unique_username, "abc123").status_code == 200
    assert first.player_info().status_code == 200          # 旧 token 此刻有效

    second = GameClient()
    assert second.login(unique_username, "abc123").status_code == 200

    assert first.player_info().status_code == 401          # 旧 token 已作废
    assert second.player_info().status_code == 200
