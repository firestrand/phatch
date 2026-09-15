from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from typing import Protocol, TypeAlias

from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import LogicalResource, ResourceProvider
from phatch.services.action_schema_types import ActionDocument, ActionSpec


@unique
class PreviewErrorCode(StrEnum):
    UNKNOWN_ACTION = "unknown_action"
    BLOCKED_ACTION = "blocked_action"
    INVALID_SEQUENCE = "invalid_sequence"
    CORRUPT_SOURCE = "corrupt_source"
    PIXEL_LIMIT = "pixel_limit"
    MEMORY_LIMIT = "memory_limit"
    INVALID_FIELD = "invalid_field"
    UNSAFE_EXPRESSION = "unsafe_expression"
    UNDECLARED_READ = "undeclared_read"
    READ_NOT_FOUND = "read_not_found"
    CONTEXT_DENIED = "context_denied"
    SOURCE_CHANGED = "source_changed"
    WORKER_FAILED = "worker_failed"
    WORKER_TIMEOUT = "worker_timeout"
    WORKER_CANCELLED = "worker_cancelled"
    STALE_REQUEST = "stale_request"


class PreviewAdmissionError(ValueError):
    __slots__ = ("action_id", "code", "field_id", "reason")

    def __init__(
        self,
        code: PreviewErrorCode,
        reason: str,
        action_id: str | None = None,
        field_id: str | None = None,
    ) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.action_id = action_id
        self.field_id = field_id

    def __str__(self) -> str:
        location = ".".join(
            value for value in (self.action_id, self.field_id) if value is not None
        )
        return f"{location}: {self.reason}" if location else self.reason


@dataclass(frozen=True, slots=True)
class PreviewSize:
    width: int
    height: int

    @property
    def pixels(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class PreviewLimits:
    max_pixels: int = 8_000_000
    max_live_bytes: int = 64 * 1024 * 1024
    frame_overhead_bytes: int = 64 * 1024


@dataclass(frozen=True, slots=True)
class PreviewSource:
    path: Path
    sha256: str
    size: PreviewSize
    mode: str
    format_name: str | None
    logical_file_info: tuple[tuple[str, str | int], ...] = ()


@dataclass(frozen=True, slots=True)
class PackagedPreviewRead:
    action_index: int
    field_id: str
    resource: LogicalResource


@dataclass(frozen=True, slots=True)
class SelectedPreviewRead:
    action_index: int
    field_id: str
    path: Path
    sha256: str


ResolvedPreviewRead: TypeAlias = PackagedPreviewRead | SelectedPreviewRead


@dataclass(frozen=True, slots=True)
class PreviewActionSpec:
    action_id: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PreviewReadContext:
    source: PreviewSource
    reads: tuple[ResolvedPreviewRead, ...]

    def open_output(self, path: Path) -> None:
        raise PreviewAdmissionError(
            PreviewErrorCode.CONTEXT_DENIED, f"preview output is denied: {path}"
        )

    def persist_metadata(self, path: Path) -> None:
        raise PreviewAdmissionError(
            PreviewErrorCode.CONTEXT_DENIED,
            f"preview metadata persistence is denied: {path}",
        )

    def run_process(self, executable: str) -> None:
        raise PreviewAdmissionError(
            PreviewErrorCode.CONTEXT_DENIED,
            f"preview process execution is denied: {executable}",
        )


@dataclass(frozen=True, slots=True)
class PreviewExecutionSpec:
    actions: tuple[PreviewActionSpec, ...]
    source: PreviewSource
    reads: tuple[ResolvedPreviewRead, ...]
    required_variables: tuple[str, ...]
    limits: PreviewLimits
    context: PreviewReadContext
    omitted_terminal_save: bool


@dataclass(frozen=True, slots=True)
class PreviewRequest:
    document: ActionDocument
    source: Path
    selected_files: tuple[Path, ...] = ()


class PreviewCatalog(Protocol):
    def action_label(self, action_id: str) -> str | None: ...

    def field_label(self, action_id: str, field_id: str) -> str | None: ...

    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]: ...


CatalogFactory: TypeAlias = Callable[[], PreviewCatalog]


@dataclass(frozen=True, slots=True)
class PreviewDependencies:
    catalog_factory: CatalogFactory
    resources: ResourceProvider
    platform: HostPlatform


@dataclass(frozen=True, slots=True)
class PreviewFileFingerprint:
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class PreviewWorkerRequest:
    request_id: str
    spec: PreviewExecutionSpec
    selected_files: tuple[PreviewFileFingerprint, ...]


@dataclass(frozen=True, slots=True)
class PreviewImagePayload:
    data: bytes
    width: int
    height: int
    mode: str
    format_name: str


@dataclass(frozen=True, slots=True)
class PreviewWorkerSuccess:
    request_id: str
    image: PreviewImagePayload
    worker_pid: int


@dataclass(frozen=True, slots=True)
class PreviewWorkerFailure:
    request_id: str
    code: PreviewErrorCode
    reason: str
    worker_pid: int


@dataclass(frozen=True, slots=True)
class PreviewWorkerCancelled:
    request_id: str
    code: PreviewErrorCode
    worker_pid: int


PreviewWorkerResult: TypeAlias = (
    PreviewWorkerSuccess | PreviewWorkerFailure | PreviewWorkerCancelled
)
