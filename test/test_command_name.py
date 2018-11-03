import pytest
from d import BaseCommand


@pytest.mark.parametrize('class_name, expected', [
    ['BuildImage', 'build-image'],
    ['BuildImageAndPush', 'build-image-and-push'],
    ['Build', 'build'],
])
def test(class_name, expected):
    BaseCommand.__name__ = class_name

    assert BaseCommand.cmd_name() == expected
