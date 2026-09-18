import pytest

from clients.game_client import GameClient

pytestmark = [pytest.mark.game, pytest.mark.regression]


@pytest.mark.smoke
@pytest.mark.parametrize("times, expected_gems", [(1, 15840), (10, 14400)])
def test_draw_costs_gems(game_client, times, expected_gems):
    data = game_client.draw(times).json()["data"]
    assert data["gems_after"] == expected_gems
    assert len(data["results"]) == times


@pytest.mark.parametrize("bad_times", [0, 2, 5, 11, -1])
def test_draw_illegal_times(game_client, bad_times):
    resp = game_client.draw(bad_times)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4005


def test_draw_without_token():
    resp = GameClient().draw(1)
    assert resp.status_code == 401
    assert resp.json()["code"] == 4003


def test_draw_insufficient_gems(game_client):
    for _ in range(10):                        # 10 次十连 = 100 抽，正好花光 16000
        assert game_client.draw(10).status_code == 200
    resp = game_client.draw(1)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4004


def test_draw_rarity_values_valid(game_client):
    results = game_client.draw(10).json()["data"]["results"]
    assert all(r["rarity"] in (3, 4, 5) for r in results)
    assert all(r["name"] for r in results)


def test_gacha_history_matches_draws(game_client):
    game_client.draw(1)
    game_client.draw(10)
    history = game_client.gacha_history(limit=50).json()["data"]
    assert len(history) == 11
    assert all(1 <= rec["pity_at_draw"] <= 90 for rec in history)
