from clients.base_client import BaseClient
from config.settings import settings


class GameClient(BaseClient):
    """模拟游戏服务器客户端：管理登录态 + 封装各接口"""

    def __init__(self, base_url: str | None = None):
        super().__init__(base_url=base_url or settings.game_api_base_url)
        self.token: str | None = None
        self.username: str | None = None

    @property
    def auth(self) -> dict:
        """带 token 的请求头；未登录时返回空"""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ---------- 账号 ----------
    def register(self, username: str, password: str):
        return self.post("/api/register", json={"username": username, "password": password})

    def login(self, username: str, password: str):
        resp = self.post("/api/login", json={"username": username, "password": password})
        if resp.status_code == 200:
            self.token = resp.json()["data"]["token"]
            self.username = username
        return resp

    def player_info(self):
        return self.get("/api/player/info", headers=self.auth)

    # ---------- 抽卡 ----------
    def draw(self, times: int = 1):
        return self.post("/api/gacha/draw", json={"times": times}, headers=self.auth)

    def gacha_history(self, limit: int = 20):
        return self.get("/api/gacha/history", params={"limit": limit}, headers=self.auth)

    # ---------- 背包 ----------
    def inventory(self):
        return self.get("/api/inventory", headers=self.auth)

    def use_item(self, item_id: str, count: int = 1):
        return self.post("/api/inventory/use", json={"item_id": item_id, "count": count}, headers=self.auth)

    # ---------- 排行榜 ----------
    def ranking(self, limit: int = 10):
        return self.get("/api/ranking", params={"limit": limit})

    def submit_score(self, score: int):
        return self.post("/api/score/submit", json={"score": score}, headers=self.auth)

    # ---------- 测试钩子 ----------
    def dev_reset(self):
        return self.post("/api/dev/reset", params={"username": self.username})

    def dev_set_pity(self, pity: int):
        return self.post("/api/dev/set_pity", json={"username": self.username, "pity": pity})

    def dev_ranking_reset(self):
        """把全局排行榜恢复成预置数据（不依赖登录态）"""
        return self.post("/api/dev/ranking/reset")
