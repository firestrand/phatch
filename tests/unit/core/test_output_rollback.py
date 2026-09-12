from __future__ import annotations

import os
from pathlib import Path

import pytest

from phatch.services.output_rollback import PublicationRollbackError
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

    with pytest.raises(PublicationRollbackError) as raised:
        transaction.publish_all()

    assert isinstance(raised.value.publication_error, PermissionError)
    rollback_destinations = {
        failure.destination for failure in raised.value.rollback_error.failures
    }
    assert rollback_destinations == set(destinations)
    assert len(tuple(tmp_path.glob(".*.bak"))) == 2
    assert not tuple(tmp_path.glob(".*.tmp"))
