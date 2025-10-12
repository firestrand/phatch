import builtins

from phatch.actions import utils


if not hasattr(builtins, '_'):
    builtins._ = lambda x: x


class DummyImageModule:
    ROTATE_90 = 2


def test_resolve_orientation_returns_constant_when_available():
    assert utils.resolve_orientation('ROTATE_90', DummyImageModule) == DummyImageModule.ROTATE_90


def test_resolve_orientation_returns_original_when_missing():
    sentinel = object()
    assert utils.resolve_orientation(sentinel, DummyImageModule) is sentinel


def test_resolve_orientation_with_none_module():
    assert utils.resolve_orientation('ROTATE_90', None) == 'ROTATE_90'
