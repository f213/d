import pytest
from d import label_and_tag


@pytest.mark.parametrize('label, expected', [
    ['f213/website', ['f213/website', None]],
    ['f213/website:tag', ['f213/website', 'tag']],
])
def test(label, expected):
    assert label_and_tag(label) == expected
