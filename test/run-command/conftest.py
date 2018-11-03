
import pytest
from d import RunCommand


@pytest.fixture
def command(mock_command):
    return mock_command(RunCommand)
