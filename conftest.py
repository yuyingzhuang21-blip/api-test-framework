import pytest

from clients.users_client import UsersClient


@pytest.fixture
def users_client():
    return UsersClient()
