from clients.base_client import BaseClient


class UsersClient(BaseClient):
    """Users 接口的专用客户端"""

    def get_user(self, user_id):
        return self.get(f"/users/{user_id}")

    def list_users(self, page: int = 1):
        return self.get("/users", params={"page": page})

    def create_user(self, payload: dict):
        return self.post("/users", json=payload)

    def update_user(self, user_id, payload: dict):
        return self.put(f"/users/{user_id}", json=payload)

    def delete_user(self, user_id):
        return self.delete(f"/users/{user_id}")
