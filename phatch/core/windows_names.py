from __future__ import annotations

from dataclasses import dataclass
from typing import Final

RESERVED_NAMES: Final = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
    | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "¹²³"}
)
FORBIDDEN: Final = frozenset('<>:"/\\|?*')


@dataclass(frozen=True, slots=True)
class WindowsNameError(ValueError):
    name: str
    reason: str

    def __str__(self) -> str:
        return f"invalid Windows filename ({self.reason}): {self.name!r}"


def windows_collision_key(name: str) -> str:
    return name.rstrip(". ").lower()


def validate_windows_name(name: str) -> str:
    if not name:
        raise WindowsNameError(name, "empty")
    if any(ord(character) < 32 or character in FORBIDDEN for character in name):
        raise WindowsNameError(name, "forbidden character")
    normalized = name.rstrip(". ")
    if normalized != name:
        raise WindowsNameError(name, "trailing dot or space")
    basename = normalized.split(".", 1)[0].rstrip(". ").upper()
    if basename in RESERVED_NAMES:
        raise WindowsNameError(name, "reserved DOS device")
    return name
