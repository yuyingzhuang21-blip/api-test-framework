import time

import requests

from config.settings import settings
from utils.logger import get_logger


class BaseClient:
    """所有 API 客户端的基类：统一管理会话、超时、重试、日志"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.session = requests.Session()

    def request(self, method: str, path: str, retries: int | None = None, **kwargs) -> requests.Response:
        url = f"{settings.api_base_url}{path}"
        kwargs.setdefault("timeout", settings.api_timeout)
        max_attempts = retries if retries is not None else settings.api_retry_count

        last_exc = None
        for attempt in range(1, max_attempts + 1):

            try:
                self.logger.info("%s %s（第 %d 次尝试）", method, url, attempt)
                resp = self.session.request(method, url, **kwargs)
                self.logger.info("响应状态码: %d", resp.status_code)
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                wait = 2 ** attempt          # 指数退避：2s, 4s, 8s...
                self.logger.warning("请求失败: %s，%d 秒后重试", exc, wait)
                time.sleep(wait)
        raise last_exc

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)
