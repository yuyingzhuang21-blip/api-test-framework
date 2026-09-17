import pytest

pytestmark = pytest.mark.negative


@pytest.mark.smoke
def test_get_nonexistent_user_returns_404(users_client):
    resp = users_client.get_user(9999)
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", ["abc", "-1", "0"])
def test_get_user_with_invalid_id(users_client, bad_id):
    resp = users_client.get_user(bad_id)
    assert resp.status_code in (400, 404), f"非法 id={bad_id} 竟然被接受了，状态码 {resp.status_code}"


def test_list_users_out_of_range_page(users_client):
    resp = users_client.list_users(page=999)
    assert resp.status_code == 200
    assert resp.json()["data"] == []
