import pytest

from d import Host


@pytest.fixture
def run(mocker):
    return mocker.patch('d.run')


@pytest.fixture
def run_with_output(mocker):
    return mocker.patch('d.run_with_output')


@pytest.fixture
def host():
    return lambda hostname: Host(hostname)


@pytest.mark.parametrize('hostname, call', [
    ['tsthost', ('ssh', 'tsthost', 'echo test')],
    ['tst.host', ('ssh', 'tst.host', 'echo test')],
    ['localhost', ['echo test']],
    [None, ['echo test']],
])
def test_ssh(host, run, hostname, call):
    host = host(hostname)
    host.run('echo test')

    run.assert_called_once_with(*call)


@pytest.mark.parametrize('hostname, call', [
    ['tsthost', ('ssh', 'tsthost', 'echo test')],
    ['tst.host', ('ssh', 'tst.host', 'echo test')],
    ['localhost', ['echo test']],
])
def test_ssh_output(host, run_with_output, hostname, call):
    host = host(hostname)
    host.get_output('echo test')

    run_with_output.assert_called_once_with(*call)


@pytest.mark.parametrize('hostname, call', [
    ['tsthost', ('ssh', 'tsthost', 'echo test')],
    ['tst.host', ('ssh', 'tst.host', 'echo test')],
    ['localhost', ['echo test']],
])
def test_ssh_json(host, run_with_output, hostname, call):
    run_with_output.return_value = '{}'  # should be valid json

    host = host(hostname)
    host.get_json('echo test')

    run_with_output.assert_called_once_with(*call)


@pytest.mark.parametrize('hostname, call', [
    ['tsthost', ('scp', 'src', 'tsthost:dst')],
    ['tst.host', ('scp', 'src', 'tst.host:dst')],
    ['localhost', ('cp', 'src', 'dst')],
])
def test_scp(host, run, hostname, call):
    host = host(hostname)
    host.cp('src', 'dst')

    run.assert_called_once_with(*call)
