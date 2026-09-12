import inspect
from pathlib import Path

import pytest
from PIL import Image

from phatch.core import preview
from phatch.core.execution_types import ExecutionIssue, IssueSeverity, IssueStage


class PreviewAction:
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last = False

    def __init__(self, label: str, color: str) -> None:
        self.label = label
        self.color = color
        self.initialized = False
        self.inputs: list[Image.Image] = []

    def init(self) -> None:
        self.initialized = True

    def apply_pil(self, image: Image.Image) -> Image.Image:
        self.inputs.append(image)
        return Image.new(image.mode, image.size, self.color)


class PreviewRegistry:
    def __init__(self, actions: tuple[PreviewAction, ...]) -> None:
        self.actions = {action.label: action for action in actions}

    def labels(self) -> tuple[str, ...]:
        return tuple(self.actions)

    def create(self, label: str) -> PreviewAction:
        return self.actions[label]


class ResultRegistry:
    def __init__(self, result: object) -> None:
        self.result = result

    def labels(self) -> tuple[str, ...]:
        return ("Action",)

    def create(self, label: str) -> object:
        return self.result


class NonImageAction:
    label = "Action"

    def init(self) -> None:
        return None

    def apply_pil(self, image: Image.Image) -> object:
        return object()


def test_generate_signature_requires_registry_and_preserves_defaults() -> None:
    signature = inspect.signature(preview.generate)
    assert tuple(signature.parameters) == (
        "source",
        "registry",
        "size",
        "path",
        "force",
    )
    assert signature.parameters["registry"].default is inspect.Parameter.empty
    assert signature.parameters["size"].default == (48, 48)
    assert signature.parameters["force"].default is True


def test_generate_opens_thumbnails_and_ensures_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "previews"
    Image.new("RGB", (200, 100), "white").save(source)
    ensured: list[str] = []
    monkeypatch.setattr(preview, "ensure_path", ensured.append)

    preview.generate(
        str(source), PreviewRegistry(()), size=(32, 32), path=str(destination)
    )

    assert ensured == [str(destination)]


def test_generate_processes_every_action_and_uses_independent_copy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "previews"
    Image.new("RGB", (20, 10), "white").save(source)
    first = PreviewAction("First", "red")
    second = PreviewAction("Second", "blue")

    preview.generate(
        str(source), PreviewRegistry((first, second)), path=str(destination)
    )

    assert first.initialized and second.initialized
    assert first.inputs[0] is not second.inputs[0]
    with Image.open(destination / "First.png") as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
    with Image.open(destination / "Second.png") as image:
        assert image.getpixel((0, 0)) == (0, 0, 255)


@pytest.mark.parametrize(("force", "expected"), [(False, "green"), (True, "red")])
def test_generate_honors_force_for_existing_preview(
    tmp_path: Path, force: bool, expected: str
) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "previews"
    destination.mkdir()
    Image.new("RGB", (8, 8), "white").save(source)
    Image.new("RGB", (8, 8), "green").save(destination / "Action.png")

    preview.generate(
        str(source),
        PreviewRegistry((PreviewAction("Action", "red"),)),
        path=str(destination),
        force=force,
    )

    with Image.open(destination / "Action.png") as image:
        expected_pixel = (0, 128, 0) if expected == "green" else (255, 0, 0)
        assert image.getpixel((0, 0)) == expected_pixel


def test_generate_uses_each_injected_catalog_independently(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (8, 6), "white").save(source)
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    preview.generate(
        str(source),
        PreviewRegistry((PreviewAction("First", "red"),)),
        path=str(first_output),
    )
    preview.generate(
        str(source),
        PreviewRegistry((PreviewAction("Second", "blue"),)),
        path=str(second_output),
    )

    assert (first_output / "First.png").is_file()
    assert not (first_output / "Second.png").exists()
    assert (second_output / "Second.png").is_file()
    assert not (second_output / "First.png").exists()


def test_generate_rejects_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(preview.openImage, "open", lambda source: None)

    with pytest.raises(OSError, match="Could not open preview source"):
        preview.generate("missing.png", PreviewRegistry(()), path=str(tmp_path))


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (object(), "require label, init, and apply_pil"),
        (
            ExecutionIssue(
                IssueStage.ACTION_INITIALIZATION,
                IssueSeverity.ERROR,
                "creation failed",
            ),
            "creation failed",
        ),
    ],
)
def test_generate_rejects_invalid_registry_result(
    tmp_path: Path, result: object, message: str
) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (8, 8), "white").save(source)

    with pytest.raises((TypeError, RuntimeError), match=message):
        preview.generate(str(source), ResultRegistry(result), path=str(tmp_path))


def test_generate_rejects_non_image_action_result(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (8, 8), "white").save(source)

    with pytest.raises(TypeError, match="must return an image"):
        preview.generate(
            str(source), ResultRegistry(NonImageAction()), path=str(tmp_path / "output")
        )


def test_main_composes_registry_from_api(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = PreviewRegistry(())
    generated: list[object] = []
    monkeypatch.setattr(preview.api, "init", lambda: registry)
    monkeypatch.setattr(
        preview, "generate", lambda source, supplied: generated.append(supplied)
    )

    preview.main()

    assert generated == [registry]
