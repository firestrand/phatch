"""Public batch controls reject invalid data before writing any outputs."""

from collections import deque
from types import SimpleNamespace

import pytest
from PIL import Image

from phatch.core import recipes
from phatch.core.capabilities import encoder_options, resolve_encoder
from phatch.core.destinations import planned_destination
from phatch.core.export_policy import (
    ExportPolicyError,
    SourceMetadata,
    capture_metadata,
    prepare_export,
    selected_tag_ids,
)
from phatch.core.variants import Variant, VariantValidationError, parse_variants
from phatch.core.workflow_preview import PreviewError, PreviewOptions, PreviewRenderer
from phatch.lib import atomic


@pytest.mark.parametrize(
    "options",
    [
        {"width": 0},
        {"height": True},
        {"format": 3},
        {"no_upscale": 1},
        {"lossless": "yes"},
        {"quality": -1},
        {"effort": 7},
        {"speed": 11},
        {"metadata_policy": "private"},
        {"color_policy": None},
        {"metadata_tags": []},
    ],
)
def test_variant_invalid_controls(options):
    with pytest.raises(VariantValidationError):
        Variant(**({"name": "small", "width": 20, "height": 10} | options))


@pytest.mark.parametrize(
    "source", [" " * 65537, "[", "[{}]", '[{"name":"bad name","width":1,"height":1}]']
)
def test_variant_definition_limits_and_locations(source):
    with pytest.raises(VariantValidationError):
        parse_variants(source)


@pytest.mark.parametrize(
    "options",
    [
        {"size": (0, 20)},
        {"size": (20,)},
        {"crop": (0, 0, 0, 2)},
        {"crop": (-1, 0, 1, 2)},
        {"crop": (0, 0, 1)},
        {"max_source_pixels": False},
        {"max_result_bytes": 0},
    ],
)
def test_preview_rejects_invalid_geometry_and_budgets(options):
    with pytest.raises(PreviewError):
        PreviewOptions(**options)


def test_preview_cache_bounds_and_clear(test_input_dir):
    with pytest.raises(PreviewError):
        PreviewRenderer(cache_bytes=-1)
    renderer = PreviewRenderer()
    source = test_input_dir / "frog.gif"
    assert renderer.render(source, []).status == "success"
    assert renderer.render(source, []).cache_hit
    renderer.clear()
    assert not renderer.render(source, []).cache_hit


@pytest.mark.parametrize(
    "document",
    [
        {1: []},
        {"description": 3, "actions": []},
        {"version": "999", "actions": []},
        {"actions": None},
        {"actions": [{"label": "Save", "plugin_id": 1, "fields": {}}]},
    ],
)
def test_legacy_recipe_shape_limits(document):
    # Python literal input preserves non-string keys for the validator.
    with pytest.raises(recipes.RecipeValidationError):
        recipes.parse_recipe(repr(document))


@pytest.mark.parametrize("contents", [b"\xff", b" " * (1024 * 1024 + 1), b"{"])
def test_recipe_file_encoding_and_size(tmp_path, contents):
    source = tmp_path / "invalid.phatch"
    source.write_bytes(contents)
    with pytest.raises(recipes.RecipeValidationError):
        recipes.read_recipe_text(source)


def test_recipe_token_limit(monkeypatch):
    monkeypatch.setattr(recipes, "MAX_TOKENS", 5)
    with pytest.raises(recipes.RecipeValidationError, match="token limit"):
        recipes.parse_recipe('{"actions": [{"label": "Save", "fields": {}}]}')


@pytest.mark.parametrize(
    "options", [{"metadata_policy": "unknown"}, {"color_policy": "unknown"}]
)
def test_export_rejects_unknown_policies(options):
    with Image.new("RGB", (2, 2)) as image, pytest.raises(ExportPolicyError):
        prepare_export(image, SourceMetadata(), "PNG", **options)


def test_selected_metadata_tags_are_bounded_and_named():
    assert selected_tag_ids(" ,271,Make") == {271}
    with pytest.raises(ExportPolicyError, match="range"):
        selected_tag_ids("65536")
    with pytest.raises(ExportPolicyError, match="Unknown"):
        selected_tag_ids("invented-tag")


@pytest.mark.parametrize("format", ["PNG", "TIFF", "JPEG", "BMP"])
def test_xmp_and_text_preservation_reports_format_limits(format, tmp_path):
    with Image.new("RGB", (4, 4)) as image:
        image.getexif()  # Initialize EXIF before exercising string XMP providers.
        image.info.update(xmp="<xmp>test</xmp>", Comment="description")
        image.format = "PNG"
        captured = capture_metadata(image)
        assert captured.xmp == b"<xmp>test</xmp>"
        for source in (
            captured,
            SourceMetadata(text={"Comment": "description"}, has_iptc=True),
        ):
            output, options, warnings = prepare_export(image, source, format)
            try:
                target = tmp_path / (format + ".image")
                output.save(target, format=format, **options)
                with Image.open(target) as saved:
                    saved.load()
                    if format == "PNG":
                        assert saved.info["Comment"] == "description"
                    elif source.xmp and format not in {"JPEG", "TIFF"}:
                        assert any("XMP" in warning for warning in warnings)
                if source.has_iptc:
                    assert any("IPTC" in warning for warning in warnings)
            finally:
                output.close()


def test_reserved_worker_destination_cannot_escape_preflight(tmp_path):
    target = tmp_path / "photo.png"
    renamed = tmp_path / "photo-1.png"
    photo = SimpleNamespace(
        planned_destinations={str(target.resolve()): deque([renamed])}
    )
    assert planned_destination(photo, target, "rename") == (renamed, "fail")
    with pytest.raises(ValueError, match="not reserved"):
        planned_destination(photo, target, "replace")


def test_atomic_rename_exhaustion_preserves_existing_targets(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="collision policy"):
        atomic.AtomicOutput(tmp_path / "bad.png", "unknown")
    targets = [tmp_path / "photo.png", tmp_path / "photo-1.png"]
    for target in targets:
        target.write_bytes(b"original")
    monkeypatch.setattr(atomic, "RENAME_ATTEMPTS", 2)
    with (
        pytest.raises(FileExistsError, match="limit"),
        atomic.AtomicOutput(targets[0], "rename") as temporary,
    ):
        temporary.write_bytes(b"new")
    assert all(target.read_bytes() == b"original" for target in targets)
    assert sorted(tmp_path.iterdir()) == sorted(targets)


@pytest.mark.parametrize(
    "format,options",
    [
        ("WEBP", {"lossless": 1}),
        ("WEBP", {"quality": True}),
        ("AVIF", {"speed": "6"}),
        ("AVIF", {"max_threads": 0}),
    ],
)
def test_encoder_control_types(format, options):
    with pytest.raises(ValueError):
        encoder_options(format, **options)
    with pytest.raises(ValueError, match="fallback"):
        resolve_encoder(format, "jpeg")


def test_variant_planning_rejects_unknown_preset_and_omits_disabled_manifest():
    from phatch.core.variants import definitions, planning_fields

    with pytest.raises(VariantValidationError, match="web or custom"):
        definitions({"Preset": "unknown"})
    planned = planning_fields(
        {"In": "/outputs", "File Name": "photo", "Write Manifest": "no"}
    )
    assert len(planned) == 6
    assert not any(artifact for _, artifact in planned)


@pytest.mark.parametrize(
    "records",
    [
        [],
        {"source": None},
        {"source": {"key": "bad"}},
        {"source": {"key": "g" * 64}},
        {"source": {"key": "0" * 64, "status": "unknown"}},
        {"source": {"key": "0" * 64, "status": "complete", "outputs": None}},
        {"source": {"key": "0" * 64, "status": "complete", "outputs": [{"path": 1}]}},
    ],
)
def test_resume_rejects_malformed_records_before_accepting_outputs(tmp_path, records):
    import json

    from phatch.core.manifests import BatchManifest, ManifestError

    journal = tmp_path / "journal.json"
    journal.write_text(json.dumps({"schema_version": 1, "records": records}))
    with pytest.raises(ManifestError):
        BatchManifest(journal, "identity", settings={}, resume=True)


def test_resume_journal_size_and_settings_are_bounded(tmp_path, monkeypatch):
    from phatch.core import manifests

    journal = tmp_path / "journal.json"
    journal.write_text('{"schema_version":1,"records":{}}')
    monkeypatch.setattr(manifests, "MAX_MANIFEST_BYTES", 4)
    with pytest.raises(manifests.ManifestError) as error:
        manifests.BatchManifest(journal, "identity", settings={}, resume=True)
    assert "size limit" in str(error.value.__cause__)
    source = tmp_path / "source.png"
    with Image.new("RGB", (2, 2)) as image:
        image.save(source)
    for settings in ({1: "value"}, {"custom": object()}):
        manifest = manifests.BatchManifest(journal, "identity", settings=settings)
        with pytest.raises(manifests.ManifestError):
            manifest.key(source, settings)


def test_fingerprint_rejects_source_changed_during_hashing(tmp_path, monkeypatch):
    from phatch.core import manifests

    source = tmp_path / "source"
    source.write_bytes(b"initial")
    real_hash = manifests.hashlib.sha256

    class ChangingHash:
        def __init__(self):
            self.digest = real_hash()
            self.changed = False

        def update(self, chunk):
            self.digest.update(chunk)
            if not self.changed:
                self.changed = True
                source.write_bytes(b"changed input")

        def hexdigest(self):
            return self.digest.hexdigest()

    monkeypatch.setattr(manifests.hashlib, "sha256", ChangingHash)
    with pytest.raises(manifests.ManifestError, match="changed"):
        manifests.file_fingerprint(source)


def test_worker_control_pipe_failures_do_not_block_shutdown(monkeypatch):
    import multiprocessing
    import threading

    from phatch.core import workers

    cancellation = threading.Event()
    monkeypatch.setattr(workers, "_CANCEL", cancellation)
    reader, writer = multiprocessing.Pipe(duplex=False)
    reader.close()
    try:
        event = workers.WorkerEvent(0, "ready")
        assert not workers._emit(writer, event)
        cancellation.set()
        assert not workers._emit(writer, event)
        assert workers._response(writer, "cancel") == "cancel"
    finally:
        writer.close()


def test_resource_contract_rejects_unknown_field_and_excess_frames(
    tmp_path, initialized_runtime
):
    from phatch.core import api
    from phatch.core.resources import (
        ResourceError,
        input_resource_identity,
        resource_identity,
    )

    class Plugin:
        label = "Invalid resources"
        resource_fields = ("Missing",)

        def _get_fields(self):
            return {}

    with pytest.raises(ResourceError, match="unknown resource field"):
        resource_identity([Plugin()], {})
    source = tmp_path / "moving.gif"
    with (
        Image.new("RGB", (4, 4), "red") as first,
        Image.new("RGB", (4, 4), "blue") as second,
    ):
        first.save(source, save_all=True, append_images=[second], duration=20)
    with pytest.raises(ResourceError, match="frame limit"):
        input_resource_identity(
            [api.ACTIONS["Watermark"]()], source, {}, {"max_sequence_frames": 1}
        )


def test_batch_result_report_cannot_replace_an_input(tmp_path):
    from phatch.core.batch import BatchResult, FileResult

    source = tmp_path / "source.png"
    source.write_bytes(b"original")
    result = BatchResult(files=[FileResult(source, status="success")])
    with pytest.raises(ValueError, match="overlaps"):
        result.write_report(source)
    assert source.read_bytes() == b"original"


@pytest.mark.parametrize("declared", ["Resource", [1]])
def test_resource_field_declarations_require_string_labels(declared):
    from phatch.core.resources import ResourceError, resource_identity

    plugin = SimpleNamespace(resource_fields=declared)
    with pytest.raises(ResourceError, match="list of field labels"):
        resource_identity([plugin], {})
