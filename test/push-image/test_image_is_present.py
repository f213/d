import pytest


@pytest.fixture
def docker(mocker):
    return mocker.patch('d.run_with_output')


def test_correct_call(docker, command):
    command.image_is_present('org/img:latest')

    docker.assert_called_once_with('docker', 'image', 'ls', '-q', 'org/img:latest')


def test_present(docker, command):
    docker.return_value = [
        '',
        'some_docker_id',
    ]

    assert command.image_is_present('test') is True


def test_not_present(docker, command):
    docker.return_value = [
        '',
    ]

    assert command.image_is_present('test') is False
