from __future__ import annotations

import builtins
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from phatch.services.output_transaction import DeferredOutputTransaction


class LegacyField(Protocol):
    def get_as_string(self) -> str: ...


class LegacyInfo(Protocol):
    def __getitem__(self, key: str, /) -> object: ...

    def set(self, key: str, value: object, /) -> None: ...


class LegacyImage(Protocol):
    def copy(self) -> LegacyImage: ...


class LegacyLayer(Protocol):
    image: LegacyImage


class NullableLegacyLayer(Protocol):
    image: LegacyImage | None


class LegacyPhotoObject(Protocol):
    @property
    def info(self) -> LegacyInfo: ...

    report_files: list[dict[str, object]]

    def get_layer(self) -> LegacyLayer | NullableLegacyLayer: ...

    def get_log(self) -> str: ...

    def clear_log(self) -> None: ...

    def set_output_transaction(
        self, transaction: DeferredOutputTransaction
    ) -> None: ...

    def close(self) -> None: ...


class LegacyActionObject(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def tags(self) -> Sequence[str]: ...

    @property
    def metadata(self) -> Sequence[str]: ...

    @property
    def valid_last(self) -> bool: ...

    @property
    def _fields(self) -> Mapping[str, LegacyField]: ...

    def _get_fields(self) -> Mapping[str, LegacyField]: ...

    def load(self, fields: Mapping[str, str]) -> list[str]: ...

    def is_enabled(self) -> bool: ...

    def is_overwrite_existing_images_forced(self) -> bool: ...

    def init(self) -> object: ...

    def is_done(self, photo: LegacyPhotoObject) -> bool: ...

    def apply(
        self,
        photo: LegacyPhotoObject,
        settings: object,
        cache: MutableMapping[str, object],
    ) -> LegacyPhotoObject: ...

    def dump(self) -> Mapping[str, object]: ...


UpdateCallback = Callable[[], None]
LegacySettings = MutableMapping[str, object]
LegacyImageInfo = MutableMapping[str, object]
LegacyPaths = Sequence[str | Path]


def translate(value: str) -> str:
    translator = getattr(builtins, "_", None)
    if callable(translator):
        return str(translator(value))
    return value
