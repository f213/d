import pytest


@pytest.fixture
def image_is_present(mocker):
    return mocker.patch('d.PushImage.image_is_present')


def test_single_push_of_the_latest(command, run, image_is_present):
    image_is_present.return_value = False

    command.handle(label='org/img')

    run.assert_called_with(['docker', 'push', 'org/img:latest'])
    assert run.call_count == 2  # only login and push org/img:latest are performed


def test_single_push_of_particular_tag(command, run):
    command.handle(label='org/img:testtag')

    run.assert_called_with(['docker', 'push', 'org/img:testtag'])
    assert run.call_count == 2  # only login and push org/img:latest are performed


def test_push_of_the_latest_and_sha1(command, run, image_is_present):
    image_is_present.return_value = True

    command.handle(
        label='org/img',
    )

    run.assert_any_call(['docker', 'push', 'org/img:latest'])
    run.assert_any_call(['docker', 'push', 'org/img:testsha1'])

# def test_(command, run, args_in_call):
#     command.handle(
#         label=['org/img1', 'org/img2'],
#     )

#     run.assert_any_call(['docker', 'push', 'org/img1'])
#     run.assert_any_call(['docker', 'push', 'org/img2'])
