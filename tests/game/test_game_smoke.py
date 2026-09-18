import pytest

pytestmark = [pytest.mark.game, pytest.mark.smoke]


def test_player_info_after_login(game_client):
    resp = game_client.player_info()
    assert resp.status_code == 200
    assert resp.json()["data"]["gems"] == 16000


def test_draw_once_consumes_gems(game_client):
    resp = game_client.draw(1)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["results"]) == 1
    assert data["gems_after"] == 16000 - 160


def test_draw_items_enter_inventory(game_client):
    game_client.draw(10)
    items = game_client.inventory().json()["data"]["items"]
    assert sum(i["count"] for i in items) == 10        # 抽到的东西全都进背包
