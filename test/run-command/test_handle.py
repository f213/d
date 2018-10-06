import pytest


@pytest.fixture(autouse=True)
def get_env(mocker):
    return mocker.patch('d.RunCommand.get_env', return_value=dict(a='b', key='value'))


def test(command, run):
    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=[])

    args = list(run.call_args[0][0])

    assert "-e 'a=b'" in args
    assert "-e 'key=value'" in args
    assert 'org/img:latest' in args


def test_remainder(command, run):
    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=['--noinput'])

    args = set(run.call_args[0][0])

    assert {'./manage.py migrate', '--noinput'}.issubset(args)


def test_no_env(command, run, get_env):
    get_env.return_value = dict()

    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=[])

    args = set(run.call_args[0][0])

    assert {'-t', 'org/img:latest'}.issubset(args)
