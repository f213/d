import pytest

from d import DeployStack, UpdateImage, get_command_registry


@pytest.fixture
def registry():
    return get_command_registry()


def test_excudes_mediator_subclasses(registry):
    assert 'manager-command' not in registry


def test_includes_other_commands(registry):
    assert 'deploy-stack' in registry

    assert registry['deploy-stack'] == DeployStack


def test_includes_subclasses(registry):
    registry['update-image'] == UpdateImage
