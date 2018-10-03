import pytest


@pytest.fixture
def service_spec(mocker):
    return mocker.patch('d.Host.ssh_json')


def test(command, service_spec):
    service_spec.return_value = [{
        'Spec': {
            'TaskTemplate': {
                'ContainerSpec': {
                    'Env': [
                        'a=b',
                        'key=value',
                    ],
                },
            },
        },
    }]

    assert command.get_env('test') == {
        'a': 'b',
        'key': 'value',
    }
