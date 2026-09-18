"""保底机制专项：随机系统里最难验证、也最容易出 bug 的部分"""
import pytest

pytestmark = [pytest.mark.game, pytest.mark.regression]


def test_hard_pity_forces_five_star(game_client):
    """硬保底：把计数设到 89，下一抽（第 90 抽）必出五星，且计数归零"""
    assert game_client.dev_set_pity(89).status_code == 200
    data = game_client.draw(1).json()["data"]
    assert data["results"][0]["rarity"] == 5
    assert data["pity_after"] == 0


def test_pity_counter_after_draw(game_client):
    """未出五星递增、出了五星归零"""
    game_client.dev_set_pity(30)
    data = game_client.draw(1).json()["data"]
    if data["results"][0]["rarity"] == 5:
        assert data["pity_after"] == 0
    else:
        assert data["pity_after"] == 31


def test_ten_draw_spanning_hard_pity_contains_five_star(game_client):
    """计数 85 起的十连：最迟在第 90 抽（本次十连的第 5 抽）触发硬保底，故本次必有五星"""
    game_client.dev_set_pity(85)
    data = game_client.draw(10).json()["data"]
    results = data["results"]

    assert any(r["rarity"] == 5 for r in results)

    # 若前 4 抽没出货，计数一路涨到 89，第 5 抽就是硬保底触发点
    if not any(r["rarity"] == 5 for r in results[:4]):
        assert results[4]["rarity"] == 5

    # 计数归零发生在「最后一次五星」那一抽之后，所以这条等式与随机性无关
    last_five = max(i for i, r in enumerate(results) if r["rarity"] == 5)
    assert data["pity_after"] == len(results) - (last_five + 1)


def test_soft_pity_raises_five_star_rate(game_client):
    """软保底：高计数区间出货率显著高于基础区间（各采样 30 次）"""
    low_hits = 0
    for _ in range(30):
        game_client.dev_set_pity(60)          # 基础概率区间（0.6%）
        low_hits += any(r["rarity"] == 5 for r in game_client.draw(1).json()["data"]["results"])

    high_hits = 0
    for _ in range(30):
        game_client.dev_set_pity(88)          # 软保底区间（约 90.6%）
        high_hits += any(r["rarity"] == 5 for r in game_client.draw(1).json()["data"]["results"])

    assert high_hits > low_hits, f"软保底未生效：基础 {low_hits}/30 vs 高计数 {high_hits}/30"
    assert high_hits >= 15, f"高计数区间出货率异常：{high_hits}/30"
