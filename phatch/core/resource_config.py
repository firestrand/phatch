from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from importlib.resources.abc import Traversable
from pathlib import Path

from phatch.resources.provider import ResourceProvider


class CompressedResourceError(RuntimeError):
    pass


def _path_values(data: Path, images: Path, locale: Path, docs: Path) -> dict[str, str]:
    return {
        "PHATCH_DOCS_PATH": str(docs),
        "PHATCH_FONTS_CACHE_PATH": str(data / "fonts.cache"),
        "PHATCH_IMAGE_PATH": str(images),
        "PHATCH_LOCALE_PATH": str(locale),
        "PHATCH_DATA_PATH": str(data),
        "PHATCH_ACTIONLISTS_PATH": str(data / "actionlists"),
        "PHATCH_BLENDER_PATH": str(data / "blender"),
        "PHATCH_FONTS_PATH": str(data / "fonts"),
        "PHATCH_HIGHLIGHTS_PATH": str(data / "highlights"),
        "PHATCH_MASKS_PATH": str(data / "masks"),
        "PHATCH_PERSPECTIVE_PATH": str(data / "perspective"),
    }


def _require_path(resource: Traversable) -> Path:
    if isinstance(resource, Path):
        return resource
    raise CompressedResourceError


@contextmanager
def packaged_config_paths(
    provider: ResourceProvider | None = None,
) -> Iterator[dict[str, str]]:
    selected = provider or ResourceProvider()
    with ExitStack() as stack:
        data = stack.enter_context(selected.tree_as_path("data"))
        images = stack.enter_context(selected.tree_as_path("images"))
        locale = stack.enter_context(selected.tree_as_path("locale"))
        docs = stack.enter_context(selected.tree_as_path("docs/html"))
        yield _path_values(data, images, locale, docs)


def direct_config_paths(provider: ResourceProvider | None = None) -> dict[str, str]:
    selected = provider or ResourceProvider()
    data = _require_path(selected.traversable("data"))
    images = _require_path(selected.traversable("images"))
    locale = _require_path(selected.traversable("locale"))
    docs = _require_path(selected.traversable("docs/html"))
    return _path_values(data, images, locale, docs)
