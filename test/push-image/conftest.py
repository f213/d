import pytest

from d import PushImage


@pytest.fixture
def command(mock_command):
    return mock_command(PushImage)


@pytest.fixture(autouse=True)
def prepare_environment(monkeypatch):
    monkeypatch.setenv('CIRCLECI', 'true')
    monkeypatch.setenv('CIRCLE_SHA1', 'testsha1')
    monkeypatch.setenv('DOCKER_LOGIN', 'mockuser')
    monkeypatch.setenv('DOCKER_PASSWORD', 'mockpw')
