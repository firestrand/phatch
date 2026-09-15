import hashlib
import json
from pathlib import Path

from phatch.services.output_publication import OutputIdentity
from phatch.services.recovery_journal import FileIdentityData, OutputIdentityData


def file_identity(path: Path) -> FileIdentityData:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": _sha256(path),
    }


def action_list_digest(actions: tuple[dict[str, str | int], ...]) -> str:
    payload = json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def identity_data(identity: OutputIdentity) -> OutputIdentityData:
    original = identity.original
    return {
        "path": str(identity.path.resolve()),
        "size": identity.size,
        "sha256": identity.sha256,
        "modified_ns": identity.modified_ns,
        "original_exists": original.existed if original is not None else None,
        "backup_path": (
            str(original.backup.resolve())
            if original is not None and original.backup is not None
            else None
        ),
    }


def output_identity(path: Path) -> OutputIdentityData:
    return {
        "path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": _sha256(path),
        "modified_ns": path.stat().st_mtime_ns,
        "original_exists": None,
        "backup_path": None,
    }


def output_matches(identity: OutputIdentityData) -> bool:
    path = Path(identity["path"])
    return (
        path.is_file()
        and path.stat().st_size == identity["size"]
        and path.stat().st_mtime_ns == identity["modified_ns"]
        and _sha256(path) == identity["sha256"]
    )


def source_matches_output(
    source: FileIdentityData,
    outputs: list[OutputIdentityData],
) -> bool:
    return any(
        output["path"] == source["path"]
        and output["size"] == source["size"]
        and output["modified_ns"] == source["modified_ns"]
        and output["sha256"] == source["sha256"]
        for output in outputs
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
