import pytest


def test_call_args(command, run_output, args_in_call):
    list(command.fetch_services('mystack'))

    call = run_output.call_args[0][0]

    assert args_in_call(['docker', 'stack', 'services', 'mystack'], call)


def test_output_parsing(command, run_output):
    run_output.return_value = "backend|org/img:latest\nworker|org/img:sha1".encode()

    got = list(command.fetch_services('mystack'))

    assert got == [
        ['backend', 'org/img:latest'],
        ['worker', 'org/img:sha1'],
    ]


@pytest.mark.parametrize('output, expected', [
    ([['backend', 'org/img:latest']], ['backend']),
    ([['backend', 'org/img:123cba']], ['backend']),
    ([['backend', 'org/other_image:123cba']], []),
    ([['backend', 'org/img:123cba']], ['backend']),
    ([['backend', 'org/img:123cba'], ['bgworker', 'org/img']], ['backend', 'bgworker']),
    ([['backend', 'org/img:123cba'], ['frontend', 'org/frontend_img'], ['bgworker', 'org/img']], ['backend', 'bgworker']),
])
def test_filtering(command, mocker, output, expected):
    mocker.patch.object(command, 'fetch_services', return_value=output)

    assert list(command.get_services('mystack', 'org/img')) == expected
