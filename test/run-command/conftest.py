
import pytest

from d import RunCommand


@pytest.fixture
def command(mocker):
    mocker.patch.object(RunCommand, 'add_arguments', return_value=None)
    mocker.patch.object(RunCommand, 'pre_add_arguments', return_value=None)
    return RunCommand()
