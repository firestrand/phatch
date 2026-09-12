import builtins
import datetime
import sys
import tomllib
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from packaging.requirements import Requirement
from PIL import Image
from rich.console import Console

from phatch.data import info
from phatch.data.version import VERSION
from phatch.lib import metadata

PROJECT_ROOT = Path(__file__).parents[2]


def load_pyproject():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)


def dependency_names(requirements: list[str]) -> set[str]:
    return {Requirement(requirement).name.lower() for requirement in requirements}


def test_package_identity_matches_current_runtime_metadata() -> None:
    # Given: the package's established runtime metadata
    # When: callers inspect its public name and version
    # Then: the historical distribution identity remains stable
    assert info.NAME == "Phatch"
    assert VERSION == "0.4.0"


def test_core_image_and_console_dependencies_support_current_behavior() -> None:
    # Given: the dependencies imported by core image and console modules
    # When: the smallest current image and console operations are exercised
    image = Image.new("RGB", (1, 1))
    console = Console(record=True, width=20)
    console.print("phatch")

    # Then: both unconditional runtime capabilities are usable
    assert image.size == (1, 1)
    assert "phatch" in console.export_text()


def test_pep517_build_system_uses_setuptools() -> None:
    # Given: the canonical project definition
    pyproject = load_pyproject()

    # When: build frontends inspect the PEP 517 contract
    build_system = pyproject["build-system"]

    # Then: setuptools is the declared backend
    assert build_system["build-backend"] == "setuptools.build_meta"
    assert dependency_names(build_system["requires"]) == {"setuptools"}


def test_pep621_metadata_declares_supported_runtime() -> None:
    # Given: the canonical project definition
    project = load_pyproject()["project"]

    # When: installers inspect package identity and compatibility
    # Then: metadata matches the supported CPython 3.11-3.13 policy
    assert project["name"] == "Phatch"
    assert project["dynamic"] == ["version"]
    assert "version" not in project
    assert project["requires-python"] == ">=3.11,<3.14"
    assert dependency_names(project["dependencies"]) == {
        "pillow",
        "platformdirs",
        "rich",
    }


def test_setuptools_reads_version_from_runtime_canonical_source() -> None:
    # Given: the setuptools dynamic metadata contract
    pyproject = load_pyproject()

    # When: the configured version source is inspected
    dynamic_version = pyproject["tool"]["setuptools"]["dynamic"]["version"]

    # Then: packaging resolves the same module attribute used at runtime
    assert dynamic_version == {"attr": "phatch.data.version.VERSION"}


def test_optional_dependencies_match_capability_boundaries() -> None:
    # Given: optional dependencies grouped by capability
    optional = load_pyproject()["project"]["optional-dependencies"]

    # When: each extra is inspected independently
    names = {
        extra: dependency_names(requirements)
        for extra, requirements in optional.items()
    }

    # Then: native and specialist integrations remain opt-in
    assert names == {
        "dev": {
            "build",
            "coverage",
            "packaging",
            "pytest",
            "pytest-cov",
            "pyinstaller",
            "pyyaml",
            "ruff",
            "spdx-tools",
            "twine",
            "ty",
        },
        "gui": {"wxpython"},
        "heif": {"pillow-heif"},
        "metadata": {"pyexiv2"},
        "windows": {"pywin32"},
    }


def test_metadata_without_native_extra_uses_portable_readers(monkeypatch) -> None:
    # Given: the optional native metadata integration is unavailable
    monkeypatch.setattr(metadata, "_PYEXIV2_AVAILABLE", False)

    # When: readers are selected for a portable image format
    readers = metadata.get_vars_by_info("image.png")

    # Then: metadata extraction uses only the portable readers
    assert readers == metadata.VARS_BY_INFO


def test_metadata_tag_policies_cover_editable_and_writable_boundaries() -> None:
    assert metadata.is_editable_tag("Exif_Image_Orientation") is True
    assert metadata.is_editable_tag("not_metadata") is False
    assert metadata.is_writable_tag("dpi") is True
    assert metadata.is_writable_tag("Exif_Image_Software") is False
    assert metadata.is_writable_tag("Exif_Image_Artist") is True
    assert metadata.is_writeable_not_exif_tag("dpi", "RGB") is True
    assert metadata.is_writeable_not_exif_tag("transparency", "P") is True
    assert metadata.is_writeable_not_exif_tag("transparency", "RGB") is False
    converted = metadata.convert_from_string("2026:09:08 01:02:03")
    assert isinstance(converted, metadata.DateTime)
    assert converted.year == 2026
    assert metadata.convert_from_string(7) == 7


class ExampleInfo(metadata._InfoCache):
    type = "Example"
    prefix = "Example_"
    _prefix_n = len(prefix)
    empty_dict: ClassVar[dict[str, int]] = {"seed": 1}

    def _extract_known(self) -> None:
        self.dict["known"] = self._source["known"]

    _extract_methods: ClassVar[dict[str, object]] = {"known": _extract_known}
    possible_vars: ClassVar[list[str]] = ["known"]

    def _get_other(self, var):
        return self._source[var]


def test_info_cache_covers_static_dynamic_and_lazy_sources(monkeypatch) -> None:
    empty = ExampleInfo()
    assert empty.dict == {"seed": 1}
    assert empty.provides("known") is True
    assert empty.provides("Example_other") is True
    assert empty.provides("unknown") is False
    assert empty.needs_orientation([]) is False
    assert empty._get_source_from_file("image.png") == "image.png"
    with pytest.raises(KeyError):
        empty._extract_other("missing")
    with pytest.raises(KeyError):
        empty._extract_other_method("missing")

    static = ExampleInfo({"known": 2, "other": 3}, ["known", "Example_other"])
    assert static._get_var_from_source_with_update("known") == 2
    assert static._get_var_from_source_with_update("known") == 2
    assert static._get_var_from_source_with_update("Example_other") == 3
    static.extract_vars()
    static.extract_vars(["known"])
    assert static.dump({"known": 4, "other": 5})["known"] == 4
    static.extract_all()

    values = iter(({"known": 6}, {"known": 7}))
    dynamic = ExampleInfo(lambda: next(values), ["known"])
    assert dynamic._get_var_from_source_with_update("known") == 6
    dynamic.dict.clear()
    assert dynamic._get_var_from_source_with_update("known") == 7

    monkeypatch.setattr(ExampleInfo, "_load_module", classmethod(lambda cls: None))
    ExampleInfo.load_module()
    assert ExampleInfo("source", [])._source == "source"
    empty.load_filename("another")


def test_info_file_extracts_paths_stats_and_missing_files(tmp_path) -> None:
    image_path = tmp_path / "nested" / "image.png"
    image_path.parent.mkdir()
    image_path.write_bytes(b"data")

    info = metadata.InfoFile(str(image_path))
    info.extract_all()
    assert info._get_var_from_source_with_update("path") == str(image_path)
    assert info._get_var_from_source_with_update("filename") == "image"
    assert info._get_var_from_source_with_update("type") == "png"
    assert info._get_var_from_source_with_update("filesize") == 4
    assert info._get_var_from_source_with_update("desktop") == metadata.DESKTOP_FOLDER
    assert metadata.InfoFile.split_vars(["path", "missing"]) == (
        {"path"},
        {"missing"},
    )

    tuple_source = metadata.InfoFile((str(image_path), str(tmp_path)))
    assert tuple_source._get_var_from_source_with_update("subfolder") == "nested"
    missing = metadata.InfoFile(str(tmp_path / "absent.png"))
    assert missing._get_var_from_source_with_update("filesize") == 0


def make_pil_source(orientation: int = 1):
    return SimpleNamespace(
        info={
            "aspect": "square",
            "compression": "raw",
            "dpi": (144, 144),
            "gamma": 2.2,
            "interlace": 1,
            "transparency": 0,
            "custom": "value",
            "exif": b"ignored",
        },
        format="PNG",
        format_description="Portable Network Graphics",
        mode="RGB",
        size=(2, 3),
        _getexif=lambda: {metadata.EXIFTAGS_REVERSE["Orientation"]: orientation},
    )


def test_pillow_info_extracts_declared_and_extra_values() -> None:
    info = metadata.InfoPil(make_pil_source(), None)
    info.extract_all()
    assert info._get_var_from_source_with_update("aspect") == "square"
    assert info._get_var_from_source_with_update("compression") == "raw"
    assert info._get_var_from_source_with_update("dpi") == 144
    assert info._get_var_from_source_with_update("format") == "PNG"
    assert (
        info._get_var_from_source_with_update("formatdescription")
        == "Portable Network Graphics"
    )
    assert info._get_var_from_source_with_update("gamma") == 2.2
    assert info._get_var_from_source_with_update("interlace") == 1
    assert info._get_var_from_source_with_update("mode") == "RGB"
    assert info._get_var_from_source_with_update("size") == (2, 3)
    assert info._get_var_from_source_with_update("transparency") == 0
    assert info._get_var_from_source_with_update("Pil_custom") == "value"
    with pytest.raises(KeyError):
        info._get_other("missing")
    info.reset_geometry()
    info.reset_geometry()
    info.set_orientation(6)
    assert info._get_var_from_source_with_update("size") == (3, 2)
    assert info.needs_orientation([]) is True


def test_pillow_metadata_adapters_cover_present_missing_and_unknown_tags(
    monkeypatch,
) -> None:
    monkeypatch.setattr(metadata, "EXIFTAGS", {1: "Orientation", 2: "Artist"})
    monkeypatch.setattr(
        metadata,
        "EXIFTAGS_REVERSE",
        {"Orientation": 1, "Artist": 2},
    )

    pexif = metadata.InfoPexif(
        SimpleNamespace(_getexif=lambda: {metadata.InfoPexif.orientation: 6, 2: "Ada"})
    )
    assert pexif._get_var_from_source_with_update("orientation") == 6
    assert pexif.provides("orientation") is True
    assert pexif.provides("Pexif_Artist") is True
    assert pexif.provides("Pexif_Unknown") is False
    assert pexif._get_other("Artist") == "Ada"
    with pytest.raises(KeyError):
        pexif._get_other("Unknown")
    pexif.extract_all()
    assert pexif.dict["Pexif_Artist"] == "Ada"

    no_exif = metadata.InfoPexif(SimpleNamespace(_getexif=lambda: None))
    assert no_exif._get_var_from_source_with_update("orientation") == 1
    broken = metadata.InfoPexif(SimpleNamespace())
    assert broken._get_var_from_source_with_update("orientation") == 1

    zexif = metadata.InfoZexif(SimpleNamespace(_getexif=lambda: {1: "value"}))
    assert zexif.provides("orientation") is True
    assert zexif.provides("Zexif_0x0001") is not None
    assert zexif.provides("Zexif_invalid") is None
    assert zexif._get_other("0x0001") == "value"
    zexif.extract_all()
    assert zexif.dict["Zexif_0x0001"] == "value"


class FakePyexiv2Source:
    def __init__(self) -> None:
        self.values = {
            "Exif.Image.Orientation": 8,
            "Exif.Image.DateTime": datetime.datetime(2026, 9, 8, 1, 2, 3),
            "Iptc.Application2.Caption": "caption",
        }

    def __getitem__(self, key):
        return self.values[key]

    def exifKeys(self):
        return ["Exif.Image.DateTime", "Exif.Image.Missing"]

    def iptcKeys(self):
        return ["Iptc.Application2.Caption"]


def test_pyexiv2_adapters_load_convert_read_and_extract(monkeypatch) -> None:
    source = FakePyexiv2Source()
    exif = metadata.InfoExif(source)
    assert exif.provides("Exif_Image_DateTime") is not None
    assert exif._get_var_from_source_with_update("orientation") == 8
    assert exif._get_other("Image_DateTime").year == 2026
    exif.extract_all()
    assert "Exif_Image_DateTime" in exif.dict

    missing_orientation = metadata.InfoExif(FakePyexiv2Source())
    del missing_orientation._source.values["Exif.Image.Orientation"]
    assert missing_orientation._get_var_from_source_with_update("orientation") == 1

    iptc = metadata.InfoIptc(source)
    iptc.extract_all()
    assert iptc.dict["Iptc_Application2_Caption"] == "caption"

    class NativeImage:
        def __init__(self, filename) -> None:
            self.filename = filename
            self.calls = []

        def readMetadata(self) -> None:
            self.calls.append("read")

        def cacheAllExifTags(self) -> None:
            self.calls.append("exif")

        def cacheAllIptcTags(self) -> None:
            self.calls.append("iptc")

    pyexiv2 = SimpleNamespace(Image=NativeImage)
    support = SimpleNamespace(
        is_readable_format=lambda image_format: image_format == "PNG"
    )
    monkeypatch.setitem(sys.modules, "pyexiv2", pyexiv2)
    monkeypatch.setitem(sys.modules, "phatch.lib._pyexiv2", support)
    metadata._InfoPyexiv2._load_module()
    loaded = metadata._InfoPyexiv2._get_source_from_file("image.png", all=True)
    assert isinstance(loaded, NativeImage)
    assert loaded.calls == ["read", "exif", "iptc"]
    assert metadata._InfoPyexiv2._get_source_from_file("image.txt") == {}


def test_legacy_exif_adapter_covers_orientation_lookup_and_expansion(
    monkeypatch,
) -> None:
    source = {
        "Image Orientation": "Rotated 90 CW",
        "EXIF Artist": "Ada",
        "Comment": "hello",
    }
    info = metadata.InfoEXIF(source)
    assert info._get_var_from_source_with_update("orientation") == 6
    assert info._get_other("Artist") == "Ada"
    assert info._get_other("Comment") == "hello"
    info.extract_all()
    assert info.dict["EXIF_Comment"] == "hello"

    fallback = metadata.InfoEXIF({})
    assert fallback._get_var_from_source_with_update("orientation") == 1
    with pytest.raises(KeyError):
        fallback._get_other("Missing")

    fake_exif = SimpleNamespace(process_file=lambda stream: {"stream": stream})
    fake_other = SimpleNamespace(EXIF=fake_exif)
    monkeypatch.setitem(sys.modules, "other", fake_other)
    metadata.InfoEXIF._load_module()


def test_reader_selection_covers_lazy_native_capability(monkeypatch) -> None:
    monkeypatch.setattr(metadata, "_PYEXIV2_AVAILABLE", True)
    load_calls = []
    monkeypatch.setattr(
        metadata._InfoPyexiv2,
        "_load_module",
        classmethod(lambda cls: load_calls.append(cls)),
    )
    monkeypatch.setattr(
        metadata._InfoPyexiv2,
        "_pyexiv2",
        SimpleNamespace(is_readable_format=lambda image_format: image_format == "PNG"),
        raising=False,
    )

    assert metadata.get_vars_by_info("image.jpg") == metadata.VARS_BY_INFO_EXIF
    assert load_calls == []
    assert metadata.get_vars_by_info("image.png") == metadata.VARS_BY_INFO_EXIF
    assert len(load_calls) == 1
    assert metadata.get_vars_by_info("image.gif") == metadata.VARS_BY_INFO
    assert len(load_calls) == 2


def test_info_test_and_extract_cover_lookup_grouping_and_dump(monkeypatch) -> None:
    test_info = metadata.InfoTest()
    assert test_info["desktop"] == metadata.INFO_TEST.get("desktop", "2")
    assert "folderindex" in test_info
    assert test_info.provides("unknown") is False
    with pytest.raises(KeyError):
        test_info["unknown"]

    class DateInfo:
        @classmethod
        def provides(cls, var):
            return var == "Pexif_DateTimeOriginal"

    with monkeypatch.context() as patch:
        patch.setattr(metadata, "INFOS", [DateInfo])
        assert test_info["Pexif_DateTimeOriginal"].year

    info = metadata.InfoExtract(vars=["path", "mode", "unknown"])
    assert info.vars_unknown == ["unknown"]
    assert metadata.InfoExtract.scan_infos(["path", "mode", "unknown"])[1] == [
        "unknown"
    ]
    assert metadata.InfoExtract.get_vars_by_info([])[1] == []

    file_source = ("/tmp/image.png", "/tmp")
    pil_source = make_pil_source()
    info.open(
        "file:///tmp/image.png",
        {metadata.InfoFile: file_source, metadata.InfoPil: pil_source},
    )
    assert info.filename == "/tmp/image.png"
    assert info["path"] == "/tmp/image.png"
    assert info.provides("mode") is True
    assert info.provides("unknown") is False
    assert set(info.types()) == {"File", "Pil"}
    assert info.dump(expand=True)["mode"] == "RGB"
    assert info.dump(free=True)["path"] == "/tmp/image.png"
    assert info.list == []

    info.set_vars([])
    monkeypatch.setattr(
        metadata,
        "get_vars_by_info",
        lambda filename: {metadata.InfoFile: ["path"]},
    )
    info.open("/tmp/other.png", {metadata.InfoFile: file_source})
    assert info.dump()["path"] == "/tmp/image.png"
    info.set(filename="/tmp/third.png")
    info.set(vars=["path"])
    info.set()
    info.clear_cache()
    info.clear()
    assert info.types() == []


def test_info_extract_orientation_expansion_and_source_updates() -> None:
    class OrientationInfo:
        type = "Orientation"
        vars: ClassVar[list[str]] = ["size"]
        dict: ClassVar[builtins.dict[str, int]] = {"orientation": 6}

        @classmethod
        def provides(cls, var):
            return var == "orientation"

        @classmethod
        def needs_orientation(cls, vars):
            return True

        def __getitem__(self, var):
            return self.dict[var]

        def set_orientation(self, orientation):
            self.orientation = orientation

        def set_source(self, source):
            self.source = source

        def extract_all(self):
            self.extracted = True

    adapter = OrientationInfo()
    info = metadata.InfoExtract(vars=["orientation"])
    info.list = [adapter]
    info.set_orientation()
    assert adapter.orientation == 6
    info.set_orientation(3)
    assert adapter.orientation == 3
    info.set_source({"Orientation": "source"})
    assert adapter.source == "source"
    info.extract_all()
    assert adapter.extracted is True
    assert info["orientation"] == 6
    with pytest.raises(KeyError):
        info["missing"]

    values = {
        "date": metadata.DateTime("2026:09:08 01:02:03"),
        "pair": (3, 4),
        "fraction": Fraction(2, 3),
        "integer": Fraction(2, 1),
    }
    metadata.InfoExtract.expand(values)
    assert values["date.year"] == 2026
    assert values["pair[1]"] == 4
    assert values["fraction.denominator"] == 3
    assert "integer.denominator" not in values


def test_dump_info_tracks_mutated_keys() -> None:
    dump = metadata.DumpInfo({"existing": 1})
    dump["new"] = 2
    assert dump == {"existing": 1, "new": 2}
    assert dump.changed == ["new"]
    assert metadata.DumpInfo().changed == []


def test_console_and_gui_scripts_use_lazy_application_entrypoint() -> None:
    # Given: standard console and GUI script declarations
    project = load_pyproject()["project"]

    # When: build tooling reads their callables
    # Then: both defer frontend selection to the existing lazy entry point
    assert project["scripts"] == {"phatch": "phatch.entrypoints:console_main"}
    assert project["gui-scripts"] == {"phatch-gui": "phatch.entrypoints:gui_main"}


def test_complete_runtime_resource_tree_is_declared_as_package_data() -> None:
    # Given: runtime assets owned by the importable data-only package
    setuptools = load_pyproject()["tool"]["setuptools"]

    # When: build tooling reads package discovery and data declarations
    # Then: every required resource subtree is included in wheels
    assert setuptools["packages"]["find"]["include"] == ["phatch*"]
    assert setuptools["package-data"]["phatch_assets"] == [
        "data/**/*",
        "docs/*",
        "docs/html/**/*",
        "images/**/*",
        "locale/**/*",
    ]


def test_quality_tools_have_explicit_incremental_configuration() -> None:
    # Given: project-local tool configuration
    tools = load_pyproject()["tool"]

    # When: quality gates load their settings
    # Then: formatting, linting, typing, tests, and branch coverage are explicit
    assert tools["ruff"]["target-version"] == "py311"
    assert tools["ruff"]["builtins"] == ["_", "_t"]
    assert {
        "phatch/other/EXIF.py",
        "tests/unit/other/test_exif_*.py",
    } <= set(tools["ruff"]["include"])
    assert tools["ruff"]["lint"]["select"]
    assert tools["ty"]["environment"]["python-version"] == "3.11"
    assert tools["pyright"]["extraPaths"] == ["."]
    assert tools["ty"]["src"]["include"] == [
        "phatch/app.py",
        "phatch/core/action_registry.py",
        "phatch/core/preview.py",
        "phatch/core/plugin_context.py",
        "phatch/core/cli.py",
        "phatch/core/config.py",
        "phatch/core/execution_ports.py",
        "phatch/core/execution_types.py",
        "phatch/core/file_references.py",
        "phatch/core/filesystem.py",
        "phatch/core/resource_config.py",
        "phatch/core/user_paths.py",
        "phatch/core/windows_names.py",
        "phatch/entrypoints.py",
        "phatch/external_tools.py",
        "phatch/services/__init__.py",
        "phatch/services/action_validation.py",
        "phatch/services/action_schema.py",
        "phatch/services/action_schema_types.py",
        "phatch/services/automation_cli.py",
        "phatch/services/automation_execution.py",
        "phatch/services/automation_report.py",
        "phatch/services/execution.py",
        "phatch/services/execution_runner.py",
        "phatch/services/image_output.py",
        "phatch/services/file_discovery.py",
        "phatch/services/legacy_actions.py",
        "phatch/services/legacy_execution.py",
        "phatch/services/legacy_recovery.py",
        "phatch/services/legacy_interaction.py",
        "phatch/services/legacy_photos.py",
        "phatch/services/legacy_types.py",
        "phatch/services/output_rollback.py",
        "phatch/services/output_transaction.py",
        "phatch/services/parallel_image_jobs.py",
        "phatch/services/parallel_image_pool.py",
        "phatch/services/parallel_save.py",
        "phatch/services/parallel_save_spec.py",
        "phatch/services/parallel_worker_bootstrap.py",
        "phatch/services/preflight.py",
        "phatch/services/recovery.py",
        "phatch/services/recovery_fingerprint.py",
        "phatch/services/recovery_journal.py",
        "phatch/services/structured_report.py",
        "phatch/actions/_blender_argv.py",
        "phatch/actions/_imagemagick_argv.py",
        "phatch/actions/_lossless_jpeg_transaction.py",
        "phatch/lib/capabilities.py",
        "phatch/lib/capability_probes.py",
        "phatch/lib/external_capability_probes.py",
        "phatch/lib/executables.py",
        "phatch/lib/image_process.py",
        "phatch/lib/image_codecs.py",
        "phatch/lib/process.py",
        "phatch/lib/reverse_translation.py",
        "phatch/lib/subprocess_runner.py",
        "phatch/lib/system.py",
        "phatch/lib/windows/locate.py",
        "phatch/lib/windows/register.py",
        "phatch/lib/windows/shortcut.py",
        "phatch/other/EXIF.py",
        "phatch/pyWx/dialog_service.py",
        "phatch/pyWx/application_branding.py",
        "phatch/pyWx/controller.py",
        "phatch/resources",
        "phatch/windows/droplet.py",
        "phatch/windows/droplet_menu.py",
        "scripts/__init__.py",
        "scripts/verify.py",
        "scripts/artifact_scan.py",
        "scripts/coverage_artifacts.py",
        "scripts/coverage_git.py",
        "scripts/distribution_smoke.py",
        "scripts/portable_smoke.py",
        "scripts/windows_window_probe.py",
        "scripts/portable_state.py",
        "scripts/release_manifest.py",
        "phatch/release_inventory.py",
    ]
    assert tools["pytest"]["ini_options"]["minversion"] == "8.4"
    assert tools["coverage"]["run"]["branch"] is True
    assert tools["coverage"]["run"]["source"] == ["phatch", "scripts"]
    assert tools["coverage"]["report"]["fail_under"] == 90.0
    assert tools["phatch"]["coverage-ratchet"] == {
        "line": 90.0,
        "branch": 90.0,
        "changed": 90.0,
        "changed-modules": [
            "phatch/app.py",
            "phatch/actions/_action_lifecycle.py",
            "phatch/actions/autocontrast.py",
            "phatch/actions/background.py",
            "phatch/actions/border.py",
            "phatch/actions/brightness.py",
            "phatch/actions/canvas.py",
            "phatch/actions/color_to_alpha.py",
            "phatch/actions/colorize.py",
            "phatch/actions/common.py",
            "phatch/actions/contour.py",
            "phatch/actions/contrast.py",
            "phatch/actions/convert_mode.py",
            "phatch/actions/copy.py",
            "phatch/actions/crop.py",
            "phatch/actions/desaturate.py",
            "phatch/actions/effect.py",
            "phatch/actions/equalize.py",
            "phatch/actions/fit.py",
            "phatch/actions/geotag.py",
            "phatch/actions/grid.py",
            "phatch/actions/highlight.py",
            "phatch/actions/invert.py",
            "phatch/actions/mask.py",
            "phatch/actions/maximum.py",
            "phatch/actions/median.py",
            "phatch/actions/minimum.py",
            "phatch/actions/mirror.py",
            "phatch/actions/offset.py",
            "phatch/actions/perspective.py",
            "phatch/actions/posterize.py",
            "phatch/actions/rank.py",
            "phatch/actions/reflection.py",
            "phatch/actions/rename.py",
            "phatch/actions/rotate.py",
            "phatch/actions/round.py",
            "phatch/actions/saturation.py",
            "phatch/actions/save.py",
            "phatch/actions/save_metadata.py",
            "phatch/actions/scale.py",
            "phatch/actions/shadow.py",
            "phatch/actions/sketch.py",
            "phatch/actions/solarize.py",
            "phatch/actions/tamogen.py",
            "phatch/actions/text.py",
            "phatch/actions/time_shift.py",
            "phatch/actions/transpose.py",
            "phatch/actions/warm_up.py",
            "phatch/actions/watermark.py",
            "phatch/actions/geek.py",
            "phatch/actions/_blender_action.py",
            "phatch/actions/_blender_argv.py",
            "phatch/actions/_blender_options.py",
            "phatch/actions/_imagemagick_action.py",
            "phatch/actions/_imagemagick_argv.py",
            "phatch/actions/_lossless_jpeg_options.py",
            "phatch/actions/_lossless_jpeg_transaction.py",
            "phatch/actions/blender.py",
            "phatch/actions/imagemagick.py",
            "phatch/actions/lossless_jpeg.py",
            "phatch/console/console.py",
            "phatch/core/api.py",
            "phatch/core/action_registry.py",
            "phatch/core/preview.py",
            "phatch/core/plugin_context.py",
            "phatch/core/cli.py",
            "phatch/core/config.py",
            "phatch/core/execution_ports.py",
            "phatch/core/execution_types.py",
            "phatch/core/file_references.py",
            "phatch/core/filesystem.py",
            "phatch/core/models.py",
            "phatch/core/pil.py",
            "phatch/core/resource_config.py",
            "phatch/core/settings.py",
            "phatch/core/user_paths.py",
            "phatch/core/windows_names.py",
            "phatch/entrypoints.py",
            "phatch/external_tools.py",
            "phatch/lib/capabilities.py",
            "phatch/lib/capability_probes.py",
            "phatch/lib/external_capability_probes.py",
            "phatch/lib/executables.py",
            "phatch/lib/image_process.py",
            "phatch/lib/image_codecs.py",
            "phatch/lib/imtools.py",
            "phatch/lib/process.py",
            "phatch/pyWx/dialog_service.py",
            "phatch/pyWx/application_branding.py",
            "phatch/pyWx/controller.py",
            "phatch/pyWx/documentation.py",
            "phatch/pyWx/frame_dependencies.py",
            "phatch/lib/metadata.py",
            "phatch/lib/openImage.py",
            "phatch/lib/reverse_translation.py",
            "phatch/lib/subprocess_runner.py",
            "phatch/lib/system.py",
            "phatch/lib/windows/locate.py",
            "phatch/lib/windows/register.py",
            "phatch/lib/windows/shortcut.py",
            "phatch/other/EXIF.py",
            "phatch/phatch.py",
            "phatch/resources/__init__.py",
            "phatch/resources/inventory.py",
            "phatch/resources/provider.py",
            "phatch/services/__init__.py",
            "phatch/services/action_list.py",
            "phatch/services/action_schema.py",
            "phatch/services/action_schema_types.py",
            "phatch/services/automation_cli.py",
            "phatch/services/automation_execution.py",
            "phatch/services/automation_report.py",
            "phatch/services/action_validation.py",
            "phatch/services/execution.py",
            "phatch/services/execution_runner.py",
            "phatch/services/image_output.py",
            "phatch/services/file_discovery.py",
            "phatch/services/legacy_actions.py",
            "phatch/services/legacy_execution.py",
            "phatch/services/legacy_recovery.py",
            "phatch/services/legacy_interaction.py",
            "phatch/services/legacy_photos.py",
            "phatch/services/legacy_types.py",
            "phatch/services/output_rollback.py",
            "phatch/services/output_transaction.py",
            "phatch/services/parallel_image_jobs.py",
            "phatch/services/parallel_image_pool.py",
            "phatch/services/parallel_save.py",
            "phatch/services/parallel_save_spec.py",
            "phatch/services/parallel_worker_bootstrap.py",
            "phatch/services/preflight.py",
            "phatch/services/recovery.py",
            "phatch/services/recovery_fingerprint.py",
            "phatch/services/recovery_journal.py",
            "phatch/services/structured_report.py",
            "phatch/windows/droplet.py",
            "phatch/windows/droplet_menu.py",
            "scripts/__init__.py",
            "scripts/artifact_scan.py",
            "scripts/coverage_artifacts.py",
            "scripts/coverage_git.py",
            "scripts/coverage_policy.py",
            "scripts/distribution_smoke.py",
            "scripts/portable_smoke.py",
            "scripts/windows_window_probe.py",
            "scripts/portable_state.py",
            "scripts/release_manifest.py",
            "phatch/release_inventory.py",
            "scripts/verify.py",
        ],
    }


def test_verification_entrypoint_is_declared_and_present() -> None:
    # Given: project verification configuration
    pyproject = load_pyproject()

    # When: a developer locates the repository gate
    # Then: its cross-platform Python entry point exists
    assert pyproject["tool"]["phatch"]["verify-script"] == "scripts/verify.py"
    assert (PROJECT_ROOT / "scripts" / "verify.py").is_file()
