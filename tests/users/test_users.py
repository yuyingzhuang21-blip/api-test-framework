import time

import pytest

from models.schemas import (
    CreateUserResponse,
    UpdateUserResponse,
    UserResponse,
    UsersListResponse,
)
from config.settings import settings
pytestmark = pytest.mark.users        # 整个文件的用例都带 users 标签


@pytest.mark.smoke
def test_get_single_user(users_client):
    resp = users_client.get_user(2)
    assert resp.status_code == 200
    parsed = UserResponse.model_validate(resp.json())
    assert parsed.data.id == 2
    assert "@" in parsed.data.email


@pytest.mark.smoke
def test_list_users_first_page(users_client):
    resp = users_client.list_users(page=1)
    assert resp.status_code == 200
    parsed = UsersListResponse.model_validate(resp.json())
    assert parsed.page == 1
    assert len(parsed.data) > 0


@pytest.mark.regression
def test_pagination_pages_do_not_overlap(users_client):
    page1 = UsersListResponse.model_validate(users_client.list_users(1).json())
    page2 = UsersListResponse.model_validate(users_client.list_users(2).json())
    ids1 = {u.id for u in page1.data}
    ids2 = {u.id for u in page2.data}
    assert page2.page == 2
    assert not (ids1 & ids2), "第 1 页和第 2 页出现了重复用户"


@pytest.mark.regression
def test_create_user(users_client):
    payload = {"name": "YY", "job": "QA"}
    resp = users_client.create_user(payload)
    assert resp.status_code == 201
    parsed = CreateUserResponse.model_validate(resp.json())
    assert parsed.name == payload["name"]
    assert parsed.id is not None


@pytest.mark.regression
def test_update_user(users_client):
    resp = users_client.update_user(2, {"name": "YY", "job": "SDET"})
    assert resp.status_code == 200
    parsed = UpdateUserResponse.model_validate(resp.json())
    assert parsed.job == "SDET"


@pytest.mark.regression
def test_delete_user(users_client):
    resp = users_client.delete_user(2)
    assert resp.status_code == 204
    assert resp.text == ""


@pytest.mark.performance
def test_get_user_response_time(users_client):
    start = time.perf_counter()
    resp = users_client.request("GET", "/users/2", retries=1)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < settings.performance_threshold_ms, (
        f"响应耗时 {elapsed_ms:.0f}ms，超过阈值 {settings.performance_threshold_ms}ms"
    )


