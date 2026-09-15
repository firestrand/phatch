from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_CREDENTIAL_PATTERNS: Final = (
    re.compile(
        r"(?i)(\bauthorization[\"']?\s*[:=]\s*[\"']?)"
        r"(?:bearer\s+)?[^\s,;\"']+"
    ),
    re.compile(
        r"(?i)(\b(?:token|password|secret|api[_-]?key)[\"']?"
        r"\s*[:=]\s*[\"']?)[^\s,;\"']+"
    ),
    re.compile(
        r"(?i)(\b(?:gps|latitude|longitude|artist|camera[_-]?serial|exif)"
        r"[\"']?\s*[:=]\s*[\"']?)[^\s,;\"']+"
    ),
    re.compile(r"(?i)(://)[^/\s@]+@"),
)


@dataclass(frozen=True, slots=True)
class SensitiveRoot:
    path: Path
    placeholder: str


@dataclass(frozen=True, slots=True)
class ReportPrivacyContext:
    roots: tuple[SensitiveRoot, ...]

    def with_paths(
        self,
        inputs: tuple[Path, ...] = (),
        outputs: tuple[Path, ...] = (),
    ) -> ReportPrivacyContext:
        roots = (*_path_roots(inputs, "input"), *_path_roots(outputs, "output"))
        unique = {root.path: root for root in (*roots, *self.roots)}
        return ReportPrivacyContext(tuple(unique.values()))


def privacy_for_paths(
    inputs: tuple[Path, ...] = (),
    outputs: tuple[Path, ...] = (),
) -> ReportPrivacyContext:
    roots = (
        *_path_roots(inputs, "input"),
        *_path_roots(outputs, "output"),
        *_system_roots(Path.home(), "<home>"),
        *_system_roots(Path(tempfile.gettempdir()), "<temp>"),
    )
    unique: dict[Path, SensitiveRoot] = {}
    for root in roots:
        unique.setdefault(root.path, root)
    return ReportPrivacyContext(tuple(unique.values()))


def privacy_for_cli_paths(
    action_list: Path,
    inputs: tuple[Path, ...],
) -> ReportPrivacyContext:
    roots = (
        *_path_roots((action_list,), "action-list"),
        *_path_roots(inputs, "input"),
        *_system_roots(Path.home(), "<home>"),
        *_system_roots(Path(tempfile.gettempdir()), "<temp>"),
    )
    unique: dict[Path, SensitiveRoot] = {}
    for root in roots:
        unique.setdefault(root.path, root)
    return ReportPrivacyContext(tuple(unique.values()))


def redact_path(path: Path, privacy: ReportPrivacyContext) -> str:
    return redact_text(str(path.resolve()), privacy)


def redact_text(value: str, privacy: ReportPrivacyContext) -> str:
    redacted = value
    ordered_roots = sorted(
        privacy.roots,
        key=lambda item: len(str(item.path)),
        reverse=True,
    )
    for root in ordered_roots:
        escaped = re.escape(str(root.path))
        redacted = re.sub(
            rf"{escaped}(?=$|[\\/\s,;:'\"\[\](){{}}])",
            root.placeholder,
            redacted,
            flags=re.IGNORECASE,
        )
    for pattern in _CREDENTIAL_PATTERNS:
        redacted = pattern.sub(r"\1<redacted>", redacted)
    return redacted


def _path_roots(paths: tuple[Path, ...], label: str) -> tuple[SensitiveRoot, ...]:
    parents = tuple(sorted({path.resolve().parent for path in paths}, key=str))
    if len(parents) == 1:
        return (SensitiveRoot(parents[0], f"<{label}>"),)
    return tuple(
        SensitiveRoot(parent, f"<{label}:{index}>")
        for index, parent in enumerate(parents, start=1)
    )


def _system_roots(path: Path, placeholder: str) -> tuple[SensitiveRoot, ...]:
    absolute = path.absolute()
    resolved = path.resolve()
    if absolute == resolved:
        return (SensitiveRoot(resolved, placeholder),)
    return (
        SensitiveRoot(resolved, placeholder),
        SensitiveRoot(absolute, placeholder),
    )
