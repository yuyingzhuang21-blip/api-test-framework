import uuid

import pytest

from clients.game_client import GameClient

pytestmark = [pytest.mark.game, pytest.mark.regression]


@pytest.fixture(autouse=True)
def reset_ranking():
    """排行榜是全局共享资源：每个用例开始前恢复预置数据。

    不加这一步，上一次运行提交的分数会一直留在服务器内存里，
    于是「我提交 999999 就应该是第 1 名」这类断言在第二次运行时必然失败——
    这就是测试间的状态污染。
    """
    resp = GameClient().dev_ranking_reset()
    assert resp.status_code == 200, f"榜单重置失败: {resp.text}"


def _new_player():
    """造一个独立的已登录账号（排行榜测试需要多个玩家）"""
    client = GameClient()
    name = "t" + uuid.uuid4().hex[:8]
    assert client.register(name, "abc123").status_code == 201
    assert client.login(name, "abc123").status_code == 200
    return client


def test_ranking_sorted_desc(game_client):
    lst = game_client.ranking().json()["data"]["list"]
    scores = [x["score"] for x in lst]
    assert scores == sorted(scores, reverse=True)
    assert lst[0]["rank"] == 1


def test_ranking_rank_definition(game_client):
    """结构不变量：名次 = 严格高于自己的分数个数 + 1 —— 与榜上有谁无关"""
    lst = game_client.ranking(100).json()["data"]["list"]
    for entry in lst:
        expected = sum(1 for x in lst if x["score"] > entry["score"]) + 1
        assert entry["rank"] == expected, f"{entry['username']} 名次错误: {entry['rank']} != {expected}"


@pytest.mark.parametrize("limit", [1, 3, 100])
def test_ranking_limit(game_client, limit):
    lst = game_client.ranking(limit).json()["data"]["list"]
    assert len(lst) <= limit


@pytest.mark.parametrize("bad_limit", [0, -1])
def test_ranking_invalid_limit(game_client, bad_limit):
    resp = game_client.ranking(bad_limit)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4009


def test_ranking_limit_capped_at_100(game_client):
    lst = game_client.ranking(999).json()["data"]["list"]
    assert len(lst) <= 100


def test_submit_score_enters_ranking(game_client):
    """榜单已重置，本次提交的 999999 唯一且最高，因此必是第 1 名（可重复执行）"""
    game_client.submit_score(999999)
    top = game_client.ranking().json()["data"]["list"][0]
    assert top["username"] == game_client.username
    assert top["rank"] == 1
    assert top["score"] == 999999


def test_lower_score_does_not_override(game_client):
    game_client.submit_score(999999)
    resp = game_client.submit_score(100)
    assert resp.json()["data"]["best_score"] == 999999


def test_submit_negative_score(game_client):
    resp = game_client.submit_score(-1)
    assert resp.status_code == 400
    assert resp.json()["code"] == 4013


def test_tied_scores_share_rank_and_skip_next():
    """并列同名次：同分并列第 1，下一名跳到第 3（榜单已重置，结果确定）"""
    a, b = _new_player(), _new_player()
    a.submit_score(888888)
    b.submit_score(888888)

    lst = GameClient().ranking(100).json()["data"]["list"]
    ranks = {x["username"]: x["rank"] for x in lst}
    assert ranks[a.username] == ranks[b.username] == 1

    following = [x for x in lst if x["rank"] > 1]
    assert following[0]["rank"] == 3, "并列之后名次应跳号（1,1,3）"
    assert following[0]["username"] == "whale_king", "并列之后应是预置榜首 9850"


def test_submit_score_requires_token():
    assert GameClient().submit_score(1).status_code == 401
