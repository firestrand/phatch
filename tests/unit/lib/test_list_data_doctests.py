import builtins
import doctest

from phatch.lib import listData


def test_list_data_examples(monkeypatch) -> None:
    translator = builtins.__dict__.get("_")
    with monkeypatch.context() as translation_state:
        translation_state.setitem(builtins.__dict__, "_", translator)
        failures, attempted = doctest.testmod(listData)

    assert attempted == 42
    assert failures == 0
    assert builtins.__dict__.get("_") is translator
