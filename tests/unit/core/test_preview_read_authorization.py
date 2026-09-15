from __future__ import annotations

from pathlib import Path

from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import ResourceProvider
from phatch.services import preview_reads
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import PreviewDependencies


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


def _dependencies(resources: Path) -> PreviewDependencies:
    resources.mkdir(parents=True, exist_ok=True)
    return PreviewDependencies(
        lambda: FixtureCatalog(),
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )


def test_external_preview_reads_list_policy_field_and_canonical_path(
    tmp_path: Path,
) -> None:
    mark = tmp_path / "custom" / "watermark.png"
    document = ActionDocument.from_values("", (("watermark", (("mark", str(mark)),)),))

    reads = preview_reads.external_preview_reads(
        document, _dependencies(tmp_path / "resources")
    )

    assert reads == (
        preview_reads.ExternalPreviewRead("watermark", "mark", mark.resolve()),
    )


def test_packaged_and_inactive_reads_need_no_authorization(tmp_path: Path) -> None:
    packaged = tmp_path / "resources" / "data" / "masks" / "daisy.png"
    packaged.parent.mkdir(parents=True)
    packaged.write_bytes(b"packaged")
    document = ActionDocument.from_values(
        "",
        (
            ("mask", (("mask", "Daisy"),)),
            (
                "background",
                (("fill", "Color"), ("mark", str(tmp_path / "ignored.png"))),
            ),
        ),
    )

    reads = preview_reads.external_preview_reads(
        document, _dependencies(tmp_path / "resources")
    )

    assert reads == ()
