import pytest

from d import UpdateImage


@pytest.fixture
def command(mock_command):
    return mock_command(UpdateImage)
