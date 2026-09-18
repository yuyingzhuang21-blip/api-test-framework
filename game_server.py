"""模拟游戏服务器：为 API 测试框架提供可控靶场。

启动：uvicorn game_server:app --reload --port 8000
文档：http://127.0.0.1:8000/docs
"""
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Game Mock Server", version="0.1")

# ---------------- 内存数据（重启即重置，测试环境天然干净） ----------------
PLAYERS: dict[str, dict] = {
    "player1": {"uid": 1001, "password": "123456", "gold": 50000, "gems": 16000, "pity": 0},
    "player2": {"uid": 1002, "password": "123456", "gold": 30000, "gems": 16000, "pity": 0},
}
TOKENS: dict[str, str] = {}          # token -> username
ITEM_TABLE: dict[str, dict] = {
    "C1001": {"name": "星穹剑", "rarity": 5},
    "C1002": {"name": "白夜之诗", "rarity": 5},
    "C2001": {"name": "苍古龙吟", "rarity": 4},
    "C2002": {"name": "晨曦短刃", "rarity": 4},
    "C3001": {"name": "新手铁剑", "rarity": 3},
    "C3002": {"name": "木质长弓", "rarity": 3},
    "C3003": {"name": "学徒法杖", "rarity": 3},
}
GACHA_POOL: dict[int, list[str]] = {          # 各稀有度的可出物品
    5: ["C1001", "C1002"],
    4: ["C2001", "C2002"],
    3: ["C3001", "C3002", "C3003"],
}
GACHA_COST = 160                              # 单抽消耗钻石

INVENTORY: dict[str, dict] = {               # username -> {item_id: count}
    "player1": {"C3001": 5, "C2001": 1},     # 预置一件，方便马上验证
}
GACHA_HISTORY: dict[str, list] = {}           # username -> [抽卡记录]
RANKING: dict[str, dict] = {                  # username -> {"uid":..., "score":...}
    "whale_king": {"uid": 2001, "score": 9850},
    "player1": {"uid": 1001, "score": 7200},
    "night_blade": {"uid": 2002, "score": 6800},
    "player2": {"uid": 1002, "score": 5400},
    "newbie_01": {"uid": 2003, "score": 1200},
}
RANKING_SEED: dict[str, dict] = {             # 预置榜单的快照，供测试钩子恢复初始状态
    name: dict(info) for name, info in RANKING.items()
}


FIVE_STAR_BASE = 0.006        # 基础五星概率 0.6%
FOUR_STAR_RATE = 0.051        # 四星概率 5.1%
SOFT_PITY_START = 74          # 第 74 抽起进入软保底
SOFT_PITY_STEP = 0.06         # 软保底每抽 +6%
HARD_PITY = 90                # 第 90 抽强制五星


def five_star_rate(pity: int) -> float:
    """pity: 距离上次出五星已经抽了多少次（0 表示刚出过）"""
    if pity + 1 >= HARD_PITY:                                  # 硬保底
        return 1.0
    return min(FIVE_STAR_BASE + max(0, pity - (SOFT_PITY_START - 1)) * SOFT_PITY_STEP, 1.0)


def roll_rarity(pity: int) -> int:
    """按当前保底计数掷一次稀有度"""
    r = random.random()
    five = five_star_rate(pity)
    if r < five:
        return 5
    if r < five + FOUR_STAR_RATE:
        return 4
    return 3

UID_SEQ = 1003


# ---------------- 请求体模型 ----------------
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str

class UseItemRequest(BaseModel):
    item_id: str
    count: int


# ---------------- 工具函数 ----------------
def get_username(authorization: str | None) -> str | None:
    """从 Authorization 头解析出用户名，无效则返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return TOKENS.get(authorization.removeprefix("Bearer ").strip())


def unauthorized() -> JSONResponse:
    return JSONResponse(status_code=401, content={"code": 4003, "msg": "未登录或凭证失效"})


# ---------------- 注册 ----------------
@app.post("/api/register", status_code=201)
def register(req: RegisterRequest):
    username = req.username.strip()
    if username in PLAYERS:
        return JSONResponse(status_code=400, content={"code": 4010, "msg": "用户名已存在"})
    if not 3 <= len(username) <= 12:
        return JSONResponse(status_code=400, content={"code": 4011, "msg": "用户名长度需为 3~12 位"})
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"code": 4012, "msg": "密码长度不能少于 6 位"})

    global UID_SEQ
    uid, UID_SEQ = UID_SEQ, UID_SEQ + 1
    PLAYERS[username] = {"uid": uid, "password": req.password, "gold": 0, "gems": 16000, "pity": 0}
    return {"code": 0, "data": {"uid": uid, "username": username, "gems": 16000}}


# ---------------- 登录 ----------------
@app.post("/api/login")
def login(req: LoginRequest):
    username = req.username.strip()
    if not username:
        return JSONResponse(status_code=400, content={"code": 4002, "msg": "用户名不能为空"})

    player = PLAYERS.get(username)
    if player is None or player["password"] != req.password:
        return JSONResponse(status_code=401, content={"code": 4001, "msg": "用户名或密码错误"})

    token = "tk_" + "".join(random.choices(string.ascii_letters + string.digits, k=16))
    # 重复登录：让该用户之前的 token 失效
    for old_token, name in list(TOKENS.items()):
        if name == username:
            del TOKENS[old_token]
    TOKENS[token] = username

    return {
        "code": 0,
        "data": {
            "uid": player["uid"],
            "username": username,
            "token": token,
            "gold": player["gold"],
            "gems": player["gems"],
        },
    }


# ---------------- 玩家信息（验证 token 机制用） ----------------
@app.get("/api/player/info")
def player_info(authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()
    player = PLAYERS[username]
    return {
        "code": 0,
        "data": {
            "uid": player["uid"],
            "username": username,
            "gold": player["gold"],
            "gems": player["gems"],
            "pity": player["pity"],
        },
    }
# ---------------- 背包查询 ----------------
@app.get("/api/inventory")
def get_inventory(authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()

    bag = INVENTORY.get(username, {})
    items = [
        {"item_id": item_id, **ITEM_TABLE.get(item_id, {"name": "未知", "rarity": 0}), "count": count}
        for item_id, count in bag.items()
        if count > 0
    ]
    return {"code": 0, "data": {"items": items}}


# ---------------- 物品使用 ----------------
@app.post("/api/inventory/use")
def use_item(req: UseItemRequest, authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()

    if req.count <= 0:
        return JSONResponse(status_code=400, content={"code": 4008, "msg": "使用数量必须大于 0"})
    if req.item_id not in ITEM_TABLE:
        return JSONResponse(status_code=400, content={"code": 4007, "msg": "物品不存在"})

    bag = INVENTORY.setdefault(username, {})
    if bag.get(req.item_id, 0) < req.count:
        return JSONResponse(status_code=400, content={"code": 4006, "msg": "物品数量不足"})

    bag[req.item_id] -= req.count
    return {"code": 0, "data": {"item_id": req.item_id, "left": bag[req.item_id]}}
class DrawRequest(BaseModel):
    times: int


# ---------------- 抽卡 ----------------
@app.post("/api/gacha/draw")
def gacha_draw(req: DrawRequest, authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()
    if req.times not in (1, 10):
        return JSONResponse(status_code=400, content={"code": 4005, "msg": "抽卡次数只能是 1 或 10"})

    player = PLAYERS[username]
    cost = GACHA_COST * req.times
    if player["gems"] < cost:
        return JSONResponse(status_code=400, content={"code": 4004, "msg": "钻石不足"})
    player["gems"] -= cost

    bag = INVENTORY.setdefault(username, {})
    history = GACHA_HISTORY.setdefault(username, [])
    results = []

    for _ in range(req.times):
        rarity = roll_rarity(player["pity"])
        item_id = random.choice(GACHA_POOL[rarity])
        is_new = bag.get(item_id, 0) == 0
        bag[item_id] = bag.get(item_id, 0) + 1

        results.append({
            "item_id": item_id,
            "name": ITEM_TABLE[item_id]["name"],
            "rarity": rarity,
            "is_new": is_new,
        })
        history.append({
            "item_id": item_id,
            "rarity": rarity,
            "pity_at_draw": player["pity"] + 1,        # 这一抽是「距上次五星的第几抽」
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        player["pity"] = 0 if rarity == 5 else player["pity"] + 1    # 出五星归零

    return {
        "code": 0,
        "data": {
            "results": results,
            "pity_after": player["pity"],
            "gems_after": player["gems"],
        },
    }


# ---------------- 抽卡历史 ----------------
@app.get("/api/gacha/history")
def get_gacha_history(limit: int = 20, authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()
    records = GACHA_HISTORY.get(username, [])
    return {"code": 0, "data": records[-limit:]}
class ScoreSubmitRequest(BaseModel):
    score: int


# ---------------- 排行榜 ----------------
@app.get("/api/ranking")
def get_ranking(limit: int = 10):
    if limit <= 0:
        return JSONResponse(status_code=400, content={"code": 4009, "msg": "limit 参数非法"})
    limit = min(limit, 100)

    ordered = sorted(RANKING.items(), key=lambda kv: kv[1]["score"], reverse=True)
    listing = []
    for idx, (username, info) in enumerate(ordered[:limit], start=1):
        score = info["score"]
        # 并列同名次：与上一名分数相同则沿用上一名的名次
        rank = listing[-1]["rank"] if listing and score == listing[-1]["score"] else idx
        listing.append({"rank": rank, "uid": info["uid"], "username": username, "score": score})

    return {"code": 0, "data": {"list": listing}}


# ---------------- 提交分数 ----------------
@app.post("/api/score/submit")
def submit_score(req: ScoreSubmitRequest, authorization: str | None = Header(default=None)):
    username = get_username(authorization)
    if username is None:
        return unauthorized()
    if req.score < 0:
        return JSONResponse(status_code=400, content={"code": 4013, "msg": "分数不能为负数"})

    entry = RANKING.setdefault(username, {"uid": PLAYERS[username]["uid"], "score": 0})
    if req.score > entry["score"]:            # 只保留历史最高分
        entry["score"] = req.score
    return {"code": 0, "data": {"username": username, "best_score": entry["score"]}}
class SetPityRequest(BaseModel):
    username: str
    pity: int


# ---------------- 测试钩子（仅本地开发使用） ----------------
@app.post("/api/dev/reset")
def dev_reset(username: str):
    """把账号恢复到初始状态，让测试可以重复执行"""
    if username not in PLAYERS:
        return JSONResponse(status_code=404, content={"code": 4014, "msg": "账号不存在"})
    PLAYERS[username]["gems"] = 16000
    PLAYERS[username]["pity"] = 0
    INVENTORY[username] = {}
    GACHA_HISTORY[username] = []
    RANKING.pop(username, None)
    return {"code": 0, "data": {"username": username, "gems": 16000, "pity": 0}}


@app.post("/api/dev/set_pity")
def dev_set_pity(req: SetPityRequest):
    """直接设置保底计数：验证硬保底这种随机撞不到的分支"""
    if req.username not in PLAYERS:
        return JSONResponse(status_code=404, content={"code": 4014, "msg": "账号不存在"})
    PLAYERS[req.username]["pity"] = req.pity
    return {"code": 0, "data": {"username": req.username, "pity": req.pity}}


@app.post("/api/dev/ranking/reset")
def dev_ranking_reset():
    """把排行榜恢复成预置数据。

    排行榜是全局共享资源，且数据会跨测试、跨运行累积；
    没有这个钩子，用例只能靠「榜单上恰好没人比我高」这种假设通过。
    """
    RANKING.clear()
    RANKING.update({name: dict(info) for name, info in RANKING_SEED.items()})
    return {"code": 0, "data": {"count": len(RANKING), "list": sorted(name for name in RANKING)}}
