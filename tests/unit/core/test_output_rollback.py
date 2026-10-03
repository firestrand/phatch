from __future__ import annotations

import os
from pathlib import Path

import pytest

from phatch.services.output_publication import PublicationFailed, PublicationSucceeded
from phatch.services.output_transaction import (
    DeferredOutputTransaction,
    NoMetadataProvider,
    OutputRequest,
)


def test_deferred_publication_discloses_rollback_denial_and_retains_backups(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    destinations = (tmp_path / "first.bin", tmp_path / "second.bin")
    for destination in destinations:
        destination.write_bytes(f"old-{destination.stem}".encode())
    real_replace = os.replace
    publication_calls = 0

    def encode(path: Path) -> None:
        path.write_bytes(b"new")

    def fail_second_publication(source: Path, destination: Path) -> None:
        nonlocal publication_calls
        publication_calls += 1
        if publication_calls == 2:
            raise PermissionError(13, "destination is locked", destination)
        real_replace(source, destination)

    def deny_restore(source: Path, destination: Path) -> None:
        if source.suffix == ".bak":
            raise PermissionError(13, "backup is locked", destination)
        real_replace(source, destination)

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", fail_second_publication
    )
    monkeypatch.setattr("phatch.services.output_rollback._SAFE_REPLACE", deny_restore)
    transaction = DeferredOutputTransaction()
    for destination in destinations:
        transaction.execute(
            OutputRequest(
                destination,
                encode,
                NoMetadataProvider(),
                lambda path: None,
            )
        )

    result = transaction.publish_all()

    assert isinstance(result, PublicationFailed)
    assert isinstance(result.cause, PermissionError)
    assert result.rollback_error is not None
    rollback_destinations = {
        failure.destination for failure in result.rollback_error.failures
    }
    assert rollback_destinations == set(destinations)
    assert len(tuple(tmp_path.glob(".*.bak"))) == 2
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_deferred_publication_refreshes_original_reserved_state(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "result.bin"
    transaction = DeferredOutputTransaction()
    transaction.execute(
        OutputRequest(
            destination,
            lambda path: path.write_bytes(b"new"),
            NoMetadataProvider(),
            lambda path: None,
        )
    )
    destination.write_bytes(b"appeared-after-prepare")

    identities = transaction.identities()
    result = transaction.publish_all()

    assert identities[0].original is not None
    assert identities[0].original.existed is True
    assert identities[0].original.backup is not None
    assert isinstance(result, PublicationSucceeded)
    assert result.outputs[0].survived is True
    assert destination.read_bytes() == b"new"
    assert not tuple(tmp_path.glob(".*.bak"))


@pytest.mark.parametrize("deny_restore", [False, True])
def test_backup_failure_restores_prior_destinations_or_reports_retained_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, deny_restore: bool
) -> None:
    from phatch.services import output_rollback

    destinations = (tmp_path / "first.bin", tmp_path / "second.bin")
    for destination in destinations:
        destination.write_bytes(b"original")
    originals = tuple(output_rollback.reserve_original(path) for path in destinations)
    real_replace = os.replace

    def fail(source: Path, destination: Path) -> None:
        if source == destinations[1]:
            raise PermissionError("backup denied")
        if deny_restore and source.suffix == ".bak":
            raise PermissionError("restore denied")
        real_replace(source, destination)

    monkeypatch.setattr(output_rollback, "_SAFE_REPLACE", fail)
    error_type = output_rollback.PublicationRollbackError if deny_restore else PermissionError
    with pytest.raises(error_type) as caught:
        output_rollback.backup_originals(originals)
    assert destinations[1].read_bytes() == b"original"
    if deny_restore:
        assert isinstance(caught.value.publication_error, PermissionError)
        assert caught.value.rollback_error.failures[0].destination == destinations[0]
        assert originals[0].backup.read_bytes() == b"original"
        assert "backup denied" in str(caught.value)
        assert "first.bin" in str(caught.value)
    else:
        assert destinations[0].read_bytes() == b"original"
        assert not tuple(tmp_path.glob(".*.bak"))
