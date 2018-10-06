import pytest

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def get_services(mocker):
    return mocker.patch('d.UpdateImage.get_services', return_value=['backend', 'frontend'])


def call(command):
    command.handle(
        name='mystack',
        image='org/img',
        remainder=['--echo-test', 'mock'],
    )


def test_args(command, run, get_services):
    call(command)

    get_services.assert_called_once_with('mystack', 'org/img')


def test_call_count(command, run):
    call(command)

    assert run.call_count == 2  # once per each service


def test_remainder(command, run, args_in_call):
    call(command)

    args = run.call_args[0][0]

    assert args_in_call(['docker', 'service', 'update'], args)
    assert args_in_call(['--image', 'org/img'], args)
    assert args_in_call(['--echo-test', 'mock', 'frontend'], args)
