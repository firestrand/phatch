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
    assert "version=VERSION" in macos_bundle[1]
