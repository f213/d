import pytest

from d import Host


@pytest.fixture
def host():
    return Host('test.mocked.host')


@pytest.fixture
def output(mocker):
    return mocker.patch('d.Host.get_output')


def test(host, output):
    output.return_value = [
        '{',
        '   "a": [',
        '       "1", 2',
        '   ]',
        '}',
    ]

    assert host.get_json('test') == {"a": ["1", 2]}
