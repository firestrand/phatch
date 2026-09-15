from pathlib import Path

import pytest

from phatch.services import output_transaction
from phatch.services.output_publication import PublicationFailed
from phatch.services.output_transaction import (
    DeferredOutputTransaction,
    NoMetadataProvider,
    OutputRequest,
)


def _transaction(destination: Path, after_publish=lambda: None):
    transaction = DeferredOutputTransaction()
    transaction.execute(
        OutputRequest(
            destination,
            lambda stage: stage.write_bytes(b"NEW_OUTPUT"),
            NoMetadataProvider(),
            lambda _stage: None,
            after_publish=after_publish,
        )
    )
    return transaction


def test_remove_backups_failure_returns_surviving_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "output.bin"
    destination.write_bytes(b"OLD_OUTPUT")
    transaction = _transaction(destination)
    monkeypatch.setattr(
        output_transaction,
        "remove_backups",
        lambda _originals: (_ for _ in ()).throw(OSError("remove backup")),
    )

    result = transaction.publish_all()

    assert isinstance(result, PublicationFailed)
    assert result.outputs[0].survived is True
    assert destination.read_bytes() == b"NEW_OUTPUT"
    assert next(iter(tmp_path.glob(".*.bak"))).read_bytes() == b"OLD_OUTPUT"


def test_after_publish_failure_returns_surviving_publication(tmp_path: Path) -> None:
    destination = tmp_path / "output.bin"
    destination.write_bytes(b"OLD_OUTPUT")
    transaction = _transaction(
        destination,
        lambda: (_ for _ in ()).throw(OSError("after publish")),
    )

    result = transaction.publish_all()

    assert isinstance(result, PublicationFailed)
    assert str(result.cause) == "after publish"
    assert result.outputs[0].survived is True
    assert destination.read_bytes() == b"NEW_OUTPUT"
    assert not tuple(tmp_path.glob(".*.bak"))


def test_discard_failure_is_aggregated_without_masking_publication_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "output.bin"
    transaction = _transaction(
        destination,
        lambda: (_ for _ in ()).throw(OSError("after publish")),
    )
    monkeypatch.setattr(
        DeferredOutputTransaction,
        "discard",
        lambda _transaction: (_ for _ in ()).throw(OSError("discard")),
    )

    result = transaction.publish_all()

    assert isinstance(result, PublicationFailed)
    assert str(result.cause) == "after publish"
    assert [str(error) for error in result.cleanup_errors] == ["discard"]
    assert result.outputs[0].survived is True
