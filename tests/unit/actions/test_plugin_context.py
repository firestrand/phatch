import shutil
from pathlib import Path
from typing import TypeAlias

from PIL import Image

from phatch.actions import common, imagemagick, save, save_metadata
from phatch.core.plugin_context import MetadataTarget as MetadataSaveTarget
from phatch.core.plugin_context import PluginContext
from phatch.external_tools import ExternalTools
from phatch.lib.capabilities import (
    Capability,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.lib.external_capability_probes import IMAGEMAGICK_6

FileCall: TypeAlias = (
    tuple[str, str] | tuple[str, str, str] | tuple[str, str, tuple[float, float]]
)


class RecordingFiles:
    def __init__(self) -> None:
        self.calls: list[FileCall] = []

    def exists(self, path: str) -> bool:
        self.calls.append(("exists", path))
        return False

    def ensure_path(self, path: str) -> None:
        self.calls.append(("ensure_path", path))

    def copy2(self, source: str, destination: str) -> None:
        self.calls.append(("copy2", source, destination))
        shutil.copy2(source, destination)

    def rename(self, source: str, destination: str) -> None:
        self.calls.append(("rename", source, destination))

    def utime(self, path: str, times: tuple[float, float]) -> None:
        self.calls.append(("utime", path, times))


class RecordingMetadata:
    def __init__(self) -> None:
        self.calls: list[tuple[MetadataSaveTarget, str]] = []

    def save(self, target: MetadataSaveTarget, filename: str) -> None:
        self.calls.append((target, filename))


class NeverRunner:
    def run(self, command, *, cancelled=None):
        raise AssertionError("runner must not run during initialization")


def external_tools(executable: str) -> ExternalTools:
    capability = Capability(
        IMAGEMAGICK_6,
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        "available",
        executable=Path(executable),
    )
    return ExternalTools(
        runner=NeverRunner(), probes=((IMAGEMAGICK_6, lambda: capability),)
    )


def plugin_context(executable: str) -> PluginContext:
    return PluginContext(
        files=RecordingFiles(),
        metadata=RecordingMetadata(),
        external_tools=external_tools(executable),
    )


class PillowLayer:
    def __init__(self, image: Image.Image) -> None:
        self.image = image

    def apply_pil(self, operation, **values) -> None:
        self.image = operation(self.image, **values)


class PillowPhoto:
    def __init__(self, image: Image.Image) -> None:
        self.info = {"size": image.size}
        self.layer = PillowLayer(image)

    def get_layer(self) -> PillowLayer:
        return self.layer


def test_distinct_contexts_survive_common_action_apply_with_real_image() -> None:
    first_context = plugin_context("/first-convert")
    second_context = plugin_context("/second-convert")
    first = common.Action(plugin_context=first_context)
    second = common.Action(plugin_context=second_context)
    source = Image.new("RGB", (3, 3), "red")

    first_photo = first.apply(PillowPhoto(source.copy()), None, {})
    second_photo = second.apply(PillowPhoto(source.copy()), None, {})

    assert first.plugin_context is first_context
    assert second.plugin_context is second_context
    assert first_photo.layer.image.getpixel((1, 1)) == (255, 0, 0)
    assert second_photo.layer.image.getpixel((1, 1)) == (255, 0, 0)


class SavePhoto:
    def __init__(self) -> None:
        self.info = {"dpi": 72}
        self.saved: list[tuple[str, str | None]] = []

    def save(self, filename, *, format, save_metadata, **options) -> None:
        self.saved.append((filename, format))


def test_save_uses_context_file_operations(monkeypatch) -> None:
    context = plugin_context("/convert")
    action = save.Action(plugin_context=context)
    photo = SavePhoto()
    monkeypatch.setattr(
        action, "is_done_info", lambda info: ("out", "out/image.png", "png")
    )
    monkeypatch.setattr(action, "get_format", lambda typ, photo=None: "PNG")
    monkeypatch.setattr(
        action,
        "get_field",
        lambda label, info: False if label == "Metadata" else 72,
    )
    monkeypatch.setattr(
        action,
        "ensure_path_or_desktop",
        lambda *args, **kwargs: "out/image.png",
    )

    action.apply(photo, lambda key: False, {})

    assert isinstance(context.files, RecordingFiles)
    assert context.files.calls == [("exists", "out/image.png")]
    assert photo.saved == [("out/image.png", "PNG")]


class MetadataPhoto:
    def __init__(self) -> None:
        self.info = {"path": "source.jpg", "size": (2, 2)}
        self.modify_date = 10.0
        self.report_files: list[str] = []

    def append_to_report(self, filename: str) -> None:
        self.report_files.append(filename)


def test_save_metadata_uses_context_operations(monkeypatch, tmp_path: Path) -> None:
    context = plugin_context("/convert")
    action = save_metadata.Action(plugin_context=context)
    photo = MetadataPhoto()
    source = tmp_path / "source.jpg"
    target = tmp_path / "target.jpg"
    Image.new("RGB", (2, 2)).save(source)
    photo.info["path"] = str(source)
    monkeypatch.setattr(
        action, "get_lossless_filename", lambda photo, info: str(target)
    )

    action.apply(photo, None, {})

    assert isinstance(context.files, RecordingFiles)
    assert isinstance(context.metadata, RecordingMetadata)
    copied = context.files.calls[0]
    assert len(copied) == 3
    assert copied[0] == "copy2"
    assert copied[1] == str(source)
    staged = copied[2]
    assert isinstance(staged, str)
    assert Path(staged).parent == tmp_path
    assert context.metadata.calls == [(photo.info, staged)]
    assert target.exists()


def test_imagemagick_initialization_preserves_each_selected_context() -> None:
    first_context = plugin_context("/first-convert")
    second_context = plugin_context("/second-convert")
    first = imagemagick.Action()
    second = imagemagick.Action()

    first.bind_plugin_context(first_context)
    second.bind_plugin_context(second_context)
    first.init()
    second.init()

    assert first.plugin_context is first_context
    assert second.plugin_context is second_context
    assert first._external_tools is first_context.external_tools
    assert second._external_tools is second_context.external_tools


def test_representative_actions_do_not_use_injected_context_by_default() -> None:
    injected = plugin_context("/injected-convert")

    action_types = (
        common.Action,
        save.Action,
        save_metadata.Action,
        imagemagick.Action,
    )
    for action_type in action_types:
        assert action_type().plugin_context is not injected


def test_default_file_operations_manage_paths_and_copies(tmp_path) -> None:
    context = default_context = common.Action().plugin_context
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    folder = tmp_path / "output"
    copied = folder / "copied.txt"

    default_context.files.ensure_path(str(folder))
    default_context.files.copy2(str(source), str(copied))

    assert context.files.exists(str(copied))
    assert copied.read_text(encoding="utf-8") == "content"


def test_default_file_operations_rename_and_update_time(tmp_path) -> None:
    files = common.Action().plugin_context.files
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("content", encoding="utf-8")

    files.rename(str(source), str(destination))
    files.utime(str(destination), (10.0, 10.0))

    assert destination.stat().st_mtime == 10.0


class MetadataTarget:
    def __init__(self) -> None:
        self.saved: list[str] = []

    def save(self, filename: str) -> None:
        self.saved.append(filename)


def test_default_metadata_operation_delegates_to_target() -> None:
    metadata = common.Action().plugin_context.metadata
    target = MetadataTarget()

    metadata.save(target, "target.jpg")

    assert target.saved == ["target.jpg"]
