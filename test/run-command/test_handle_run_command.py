import pytest


@pytest.fixture(autouse=True)
def get_env(mocker):
    return mocker.patch('d.RunCommand.get_env', return_value=dict(a='b', key='value'))


def test(command, run):
    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=[])

    args = list(run.call_args[0][0])

    assert "-ea=b" in args
    assert "-ekey=value" in args
    assert 'org/img:latest' in args


def test_remainder(command, run, args_in_call):
    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=['--noinput'])

    assert args_in_call(['./manage.py migrate', '--noinput'], run.call_args[0][0])


def test_no_env(command, run, get_env, args_in_call):
    get_env.return_value = dict()

    command.handle(env_from='test', image='org/img:latest', command='./manage.py migrate', remainder=[])

    assert args_in_call(['-t', 'org/img:latest'], run.call_args[0][0])
