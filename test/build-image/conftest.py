import pytest
from d import BuildImage


@pytest.fixture
def command(mock_command):
    return mock_command(BuildImage)


@pytest.fixture(autouse=True)
def prepare_environment(monkeypatch):
    monkeypatch.setenv('CIRCLECI', 'true')
    monkeypatch.setenv('CIRCLE_SHA1', 'testsha1')
