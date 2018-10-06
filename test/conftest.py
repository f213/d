import pytest


@pytest.fixture
def run(mocker):
    """Mock the app-wide run command"""
    return mocker.patch('d.subprocess.check_call')


@pytest.fixture
def run_output(mocker):
    """Mock the run command that returns output"""
    return mocker.patch('d.subprocess.check_output')


@pytest.fixture
def args_in_call():
    def _args(args, call_args):
        for i in range(0, len(call_args) - len(args) + 1):
            if call_args[i:i + len(args)] == args:
                return True

        return False

    return _args


@pytest.fixture
def mock_command(mocker):
    """Apply some mutations to the command to make it usable in the test env"""
    def _mock_command(command_class):
        mocker.patch.object(command_class, 'add_arguments', return_value=None)
        mocker.patch.object(command_class, 'pre_add_arguments', return_value=None)
        instance = command_class()

        if hasattr(instance, 'host'):
            instance.host.name = '==MOCKED_HOST=='

        return instance

    return _mock_command
