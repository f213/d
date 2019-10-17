import pytest

from d import flatten_args


@pytest.mark.parametrize('args, expected', [
    ([['docker', 'build'], '-t'], ['docker', 'build', '-t']),
    ([['docker', 'build'], '-t', ['org/img', '-f', 'Dockerfile']], ['docker', 'build', '-t', 'org/img', '-f', 'Dockerfile']),
    (['-t', '-i'], ['-t', '-i']),
    (['-t', 5], ['-t', '5']),
    (['-t', [], 5], ['-t', '5']),
    (['-t', [], u'weird'], ['-t', 'weird']),
    ([['-t', '-i']], ['-t', '-i']),
])
def test(args, expected):
    assert flatten_args(args) == expected


@pytest.mark.parametrize('args', [
    ['-t', None],
    ['-t', lambda: 'fail'],
])
def test_error(args):
    with pytest.raises(TypeError):
        flatten_args(args)
