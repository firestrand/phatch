from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final, TypeAlias, TypedDict

_SCHEMA_VERSION: Final = 1
JsonValue: TypeAlias = (
    str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None
)
JsonObject: TypeAlias = dict[str, JsonValue]


class JournalState(StrEnum):
    PREPARED = "prepared"
    COMPLETED = "completed"
    FAILED = "failed"


class FileIdentityData(TypedDict):
    path: str
    size: int
    modified_ns: int
    sha256: str


class OutputIdentityData(TypedDict):
    path: str
    size: int
    sha256: str
    modified_ns: int
    original_exists: bool | None
    backup_path: str | None


class JournalRecordData(TypedDict):
    version: int
    timestamp: str
    input: FileIdentityData
    action_digest: str
    outputs: list[OutputIdentityData]
    state: str
    issues: list[str]


class JournalCorruptionError(RuntimeError):
    __slots__ = ("line", "path")

    def __init__(self, path: Path, line: int) -> None:
        self.path = path
        self.line = line
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"corrupt recovery journal {self.path} at line {self.line}"


class JournalWriteError(OSError):
    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"incomplete recovery journal write: {path}")


class JournalFormatError(ValueError):
    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class RecoveryJournal:
    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: JournalRecordData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.read_bytes().endswith(b"\n"):
            valid_size = sum(
                len(line)
                for line in self.path.read_bytes().splitlines(keepends=True)
                if line.endswith(b"\n")
            )
            with self.path.open("r+b") as stream:
                stream.truncate(valid_size)
                os.fsync(stream.fileno())
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        previous_size = self.path.stat().st_size if self.path.exists() else 0
        try:
            with self.path.open("ab", buffering=0) as stream:
                encoded = payload + b"\n"
                if stream.write(encoded) != len(encoded):
                    raise JournalWriteError(self.path)
                os.fsync(stream.fileno())
        except OSError:
            with self.path.open("r+b") as stream:
                stream.truncate(previous_size)
                os.fsync(stream.fileno())
            raise

    def records(self) -> tuple[JournalRecordData, ...]:
        if not self.path.exists():
            return ()
        lines = self.path.read_bytes().splitlines(keepends=True)
        records: list[JournalRecordData] = []
        for index, line in enumerate(lines, 1):
            if index == len(lines) and not line.endswith(b"\n"):
                break
            try:
                records.append(_parse_record(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise JournalCorruptionError(self.path, index) from error
        return tuple(records)


def record_data(
    identity: FileIdentityData,
    action_digest: str,
    outputs: list[OutputIdentityData],
    state: JournalState,
    issues: list[str],
) -> JournalRecordData:
    return {
        "version": _SCHEMA_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "input": identity,
        "action_digest": action_digest,
        "outputs": outputs,
        "state": state.value,
        "issues": issues,
    }


def _parse_record(raw: JsonObject) -> JournalRecordData:
    if raw["version"] != _SCHEMA_VERSION:
        raise JournalFormatError("unsupported recovery journal version")
    timestamp = str(raw["timestamp"])
    parsed_time = datetime.fromisoformat(timestamp)
    if parsed_time.tzinfo is None or parsed_time.utcoffset() != UTC.utcoffset(
        parsed_time
    ):
        raise JournalFormatError("journal timestamp must be UTC")
    input_data = raw["input"]
    outputs_data = raw["outputs"]
    issues_data = raw["issues"]
    if not isinstance(input_data, dict) or not isinstance(outputs_data, list):
        raise JournalFormatError("invalid recovery journal record")
    if not isinstance(issues_data, list) or not all(
        isinstance(issue, str) for issue in issues_data
    ):
        raise JournalFormatError("invalid recovery journal issues")
    action_digest = raw["action_digest"]
    state = raw["state"]
    if not isinstance(action_digest, str) or not isinstance(state, str):
        raise JournalFormatError("invalid recovery journal state")
    return {
        "version": _SCHEMA_VERSION,
        "timestamp": timestamp,
        "input": _parse_input(input_data),
        "action_digest": action_digest,
        "outputs": [_parse_output(output) for output in outputs_data],
        "state": JournalState(state).value,
        "issues": [str(issue) for issue in issues_data],
    }


def _parse_input(raw: JsonObject) -> FileIdentityData:
    path = raw.get("path")
    size = raw.get("size")
    modified_ns = raw.get("modified_ns")
    sha256 = raw.get("sha256")
    if not isinstance(path, str) or not isinstance(size, int):
        raise JournalFormatError("invalid recovery input identity")
    if not isinstance(modified_ns, int) or not isinstance(sha256, str):
        raise JournalFormatError("invalid recovery input identity")
    return {"path": path, "size": size, "modified_ns": modified_ns, "sha256": sha256}


def _parse_output(raw: JsonValue) -> OutputIdentityData:
    if not isinstance(raw, dict):
        raise JournalFormatError("invalid recovery output identity")
    path = raw.get("path")
    size = raw.get("size")
    sha256 = raw.get("sha256")
    modified_ns = raw.get("modified_ns")
    original_exists = raw.get("original_exists")
    backup_path = raw.get("backup_path")
    if not isinstance(path, str) or not isinstance(size, int):
        raise JournalFormatError("invalid recovery output identity")
    if not isinstance(sha256, str) or not isinstance(modified_ns, int):
        raise JournalFormatError("invalid recovery output identity")
    if original_exists is not None and not isinstance(original_exists, bool):
        raise JournalFormatError("invalid recovery output original state")
    if backup_path is not None and not isinstance(backup_path, str):
        raise JournalFormatError("invalid recovery output backup path")
    if original_exists is True and backup_path is None:
        raise JournalFormatError("existing recovery output requires backup path")
    if original_exists is False and backup_path is not None:
        raise JournalFormatError("new recovery output cannot have backup path")
    if backup_path is not None:
        destination = Path(path)
        backup = Path(backup_path)
        expected_prefix = f".{destination.name}."
        if (
            backup.parent != destination.parent
            or not backup.name.startswith(expected_prefix)
            or backup.suffix != ".bak"
        ):
            raise JournalFormatError("invalid recovery output backup location")
    return {
        "path": path,
        "size": size,
        "sha256": sha256,
        "modified_ns": modified_ns,
        "original_exists": original_exists,
        "backup_path": backup_path,
    }
