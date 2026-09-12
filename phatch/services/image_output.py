from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL.Image import Image

from phatch.lib import imtools, openImage
from phatch.services.output_transaction import (
    AtomicOutputTransaction,
    NativeMetadataProvider,
    NoMetadataProvider,
    OutputIdentity,
    OutputRequest,
    OutputTransaction,
    PillowValidator,
)

SaveOption = int | str | tuple[int, int]


@dataclass(frozen=True, slots=True)
class RenderedImage:
    image: Image
    thumbnail_data: bytes | str | None


class MetadataSource(Protocol):
    def save(
        self,
        target: str,
        target_format: str | None = None,
        thumbdata: bytes | str | None = None,
    ) -> str | None: ...


@dataclass(frozen=True, slots=True)
class MetadataCopyRequest:
    source: Path
    destination: Path
    format_name: str
    copy_source: Callable[[Path], None]
    write_metadata: Callable[[Path], str | None]
    modified_time_ns: int | None = None
    expected_size: tuple[int, int] | None = None
    after_publish: Callable[[], None] = lambda: None


@dataclass(frozen=True, slots=True)
class ImageSaveRequest:
    destination: Path
    rendered: RenderedImage
    format_name: str
    options: dict[str, SaveOption]
    compression: str
    metadata_source: MetadataSource | None
    modified_time_ns: int | None
    log_conversion: Callable[[str, str], None]
    after_publish: Callable[[], None] = lambda: None


def render_image(
    image: Image,
    format_name: str,
    reverse_orientation: tuple[int, ...] | None,
    preserve_metadata: bool,
) -> RenderedImage:
    from phatch.lib import thumbnail

    rendered = imtools.convert_save_mode_by_format(image, format_name)
    if not preserve_metadata:
        return RenderedImage(rendered, None)
    thumb = thumbnail.thumbnail(rendered, (160, 160))
    thumbnail_data = imtools.get_format_data(thumb, format_name)
    return RenderedImage(
        imtools.transpose(rendered, reverse_orientation or ()), thumbnail_data
    )


@dataclass(frozen=True, slots=True)
class LegacyImageEncoder:
    rendered: Image
    format_name: str
    options: dict[str, SaveOption]
    compression: str
    log_conversion: Callable[[str, str], None]

    def __call__(self, path: Path) -> None:
        if self.compression.lower() not in ("raw", "none"):
            openImage.check_libtiff(self.compression)
            writer = openImage.save_libtiff
            if writer is None:
                raise OSError("libtiff writer is unavailable")
            writer(
                self.rendered,
                str(path),
                compression=self.compression,
                **self.options,
            )
            return
        save_options = dict(self.options)
        save_options["format"] = self.format_name
        file_mode = imtools.save_check_mode(self.rendered, str(path), **save_options)
        if not file_mode:
            return
        if self.rendered.mode.endswith("A") and not file_mode.endswith("A"):
            converted = self.rendered.convert("RGBA")
            fallback_mode = imtools.save_check_mode(
                converted, str(path), **save_options
            )
            self.log_conversion(
                self.rendered.mode,
                fallback_mode if fallback_mode else "RGBA",
            )
            return
        self.log_conversion(self.rendered.mode, file_mode)


def save_transactionally(
    request: ImageSaveRequest,
    transaction: OutputTransaction | None = None,
) -> OutputIdentity:
    metadata = NoMetadataProvider()
    if request.metadata_source is not None:
        metadata_source = request.metadata_source

        def write_metadata(path: Path) -> str | None:
            return metadata_source.save(
                str(path), request.format_name, request.rendered.thumbnail_data
            )

        metadata = NativeMetadataProvider(write_metadata)
    output_transaction = transaction or AtomicOutputTransaction()
    return output_transaction.execute(
        OutputRequest(
            request.destination,
            LegacyImageEncoder(
                request.rendered.image,
                request.format_name,
                request.options,
                request.compression,
                request.log_conversion,
            ),
            metadata,
            PillowValidator(request.format_name, request.rendered.image.size),
            request.modified_time_ns,
            request.after_publish,
        )
    )


def save_metadata_transactionally(
    request: MetadataCopyRequest,
    transaction: OutputTransaction | None = None,
) -> OutputIdentity:
    output_transaction = transaction or AtomicOutputTransaction()
    return output_transaction.execute(
        OutputRequest(
            request.destination,
            request.copy_source,
            NativeMetadataProvider(request.write_metadata),
            PillowValidator(request.format_name, request.expected_size),
            request.modified_time_ns,
            request.after_publish,
        )
    )
