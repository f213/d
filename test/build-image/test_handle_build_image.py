import pytest


@pytest.fixture(autouse=True)
def tag_as_latest(mocker):
    mocker.patch('d.BuildImage.tag_as_latest')


def test(command, run, args_in_call):
    command.handle(
        label='org/img',
        ctx='src',
        tag_method='sha1',
        remainder=['--build-arg', 'foo=bar'],
    )

    call = run.call_args[0][0]

    assert args_in_call(['docker', 'build', '-t', 'org/img:testsha1'], call)
    assert args_in_call(['--build-arg', 'foo=bar', 'src'], call)
