import pytest


@pytest.mark.parametrize('label, expected', [
    ['f213/website', 'f213/website:testsha1'],
    ['f213/website:forcedlabel', 'f213/website:forcedlabel'],

])
def test_default_taging(command, label, expected):
    assert command.label(label) == expected


@pytest.mark.freeze_time('2032-12-01 15:30')
def test_taging_by_date(command):
    assert command.label('f213/website', tag_method='date') == 'f213/website:203212011530'


@pytest.mark.parametrize('label, tag, expected', [
    ['f213/website', 'latest', 'f213/website:latest'],
    ['f213/website', '', 'f213/website:testsha1'],  # the default tag
])
def test_taging_with_given_tag(command, label, tag, expected):
    assert command.label(label, tag) == expected
