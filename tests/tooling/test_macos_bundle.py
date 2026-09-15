from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]


@pytest.mark.unit
def test_pyinstaller_spec_declares_native_macos_application_identity() -> None:
    # Given: the cross-platform PyInstaller release specification
    spec = (PROJECT_ROOT / "packaging" / "phatch.spec").read_text(encoding="utf-8")

    # When: the macOS bundle contract is inspected
    macos_bundle = spec.split("app = BUNDLE(", maxsplit=1)

    # Then: LaunchServices receives the canonical product identity and version
    assert len(macos_bundle) == 2
    assert 'name="Phatch.app"' in macos_bundle[1]
    assert '"CFBundleName": NAME' in macos_bundle[1]
    assert '"CFBundleDisplayName": NAME' in macos_bundle[1]
    assert "version=MACOS_VERSION" in macos_bundle[1]
    assert '"CFBundleVersion": MACOS_BUILD_VERSION' in macos_bundle[1]
    assert '"LSMinimumSystemVersion": "14.0"' in macos_bundle[1]


@pytest.mark.unit
def test_pyinstaller_spec_collects_action_sources_for_runtime_discovery() -> None:
    # Given: action discovery scans the installed package directory for Python files
    spec = (PROJECT_ROOT / "packaging" / "phatch.spec").read_text(encoding="utf-8")
    constants = (PROJECT_ROOT / "phatch" / "core" / "ct.py").read_text(encoding="utf-8")

    # When/Then: the frozen package retains those physical action sources
    assert '(root / "phatch" / "actions").glob("*.py")' in spec
    assert '"phatch/actions"' in spec
    assert '(root / "phatch").rglob("*.py")' in spec
    assert "set(package_modules)" in spec
    runtime_hooks = spec.split("runtime_hooks =", maxsplit=1)[1].split(
        "console_analysis =", maxsplit=1
    )[0]
    assert "runtime_phatch_legacy_imports.py" in runtime_hooks
    assert "if is_macos" not in runtime_hooks
    assert "sys, '_MEIPASS', os.path.dirname(os.path.dirname(FILE))" in constants
    assert "BUNDLE_PATH, 'phatch', 'actions'" in constants


@pytest.mark.unit
def test_pyinstaller_spec_registers_required_preview_runtime_modules() -> None:
    # Given: the runtime inventory and frozen application specification
    spec = (PROJECT_ROOT / "packaging" / "phatch.spec").read_text(encoding="utf-8")

    # When/Then: frozen hidden imports consume the same explicit module contract
    assert "REQUIRED_RUNTIME_MODULES" in spec
    assert "set(REQUIRED_RUNTIME_MODULES)" in spec
