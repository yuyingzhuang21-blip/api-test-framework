import pytest

from clients.game_client import GameClient

pytestmark = [pytest.mark.game, pytest.mark.regression]


def test_new_player_inventory_is_empty(game_client):
    assert game_client.inventory().json()["data"]["items"] == []


def test_draw_then_use_item(game_client):
    game_client.draw(10)
    items = game_client.inventory().json()["data"]["items"]
    assert items, "十连之后背包不应为空"

    target = items[0]
    resp = game_client.use_item(target["item_id"], 1)
    assert resp.status_code == 200
    assert resp.json()["data"]["left"] == target["count"] - 1


def test_use_more_than_owned(game_client):
    game_client.draw(10)
    target = game_client.inventory().json()["data"]["items"][0]
    resp = game_client.use_item(target["item_id"], target["count"] + 1)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4006


def test_use_nonexistent_item(game_client):
    resp = game_client.use_item("X999", 1)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4007


@pytest.mark.parametrize("bad_count", [0, -1])
def test_use_invalid_count(game_client, bad_count):
    resp = game_client.use_item("C3001", bad_count)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4008


def test_inventory_requires_token():
    assert GameClient().inventory().status_code == 401


def test_use_item_requires_token():
    assert GameClient().use_item("C3001", 1).status_code == 401
