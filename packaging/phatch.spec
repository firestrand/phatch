import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

from phatch.data.info import NAME
from phatch.data.version import VERSION


root = Path(SPEC).resolve().parents[1]
is_macos = sys.platform == "darwin"
console_executable_name = "Phatch-CLI" if is_macos else "Phatch"
gui_executable_name = NAME if is_macos else "Phatch-GUI"
data_files = collect_data_files("phatch_assets") + [
    (str(root / "COPYING"), "."),
    (str(root / "AUTHORS"), "."),
    (str(root / "packaging" / "portable-data" / ".keep"), "portable-data"),
]
hidden_imports = (
    collect_submodules("phatch.actions")
    + collect_submodules("phatch.core")
    + collect_submodules("phatch.data")
    + collect_submodules("phatch.lib")
    + collect_submodules("phatch.other")
    + collect_submodules("phatch.services")
    + collect_submodules("phatch.pyWx")
)
hook_paths = [str(root / "packaging" / "hooks")]
runtime_hooks = (
    []
    if is_macos
    else [str(root / "packaging" / "hooks" / "runtime_phatch_legacy_imports.py")]
)

console_analysis = Analysis(
    [str(root / "packaging" / "console_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=hook_paths,
    runtime_hooks=runtime_hooks,
    noarchive=False,
)
gui_analysis = Analysis(
    [str(root / "packaging" / "gui_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=hook_paths,
    runtime_hooks=runtime_hooks,
    noarchive=False,
)
if not is_macos:
    MERGE(
        (console_analysis, console_executable_name, console_executable_name),
        (gui_analysis, gui_executable_name, gui_executable_name),
    )

console_pyz = PYZ(console_analysis.pure)
console_exe = EXE(
    console_pyz,
    console_analysis.dependencies,
    console_analysis.scripts,
    [],
    exclude_binaries=True,
    name=console_executable_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(root / "phatch_assets" / "images" / "icons" / "64x64" / "phatch.ico"),
)
gui_pyz = PYZ(gui_analysis.pure)
gui_exe = EXE(
    gui_pyz,
    gui_analysis.dependencies,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name=gui_executable_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "phatch_assets" / "images" / "icons" / "64x64" / "phatch.ico"),
)

if is_macos:
    collection = COLLECT(
        gui_exe,
        gui_analysis.binaries,
        gui_analysis.datas,
        strip=False,
        upx=False,
        name="Phatch",
    )
    app = BUNDLE(
        collection,
        name="Phatch.app",
        bundle_identifier="org.phatch.Phatch",
        version=VERSION,
        info_plist={
            "CFBundleName": NAME,
            "CFBundleDisplayName": NAME,
        },
    )
else:
    collection = COLLECT(
        console_exe,
        gui_exe,
        console_analysis.binaries,
        console_analysis.datas,
        gui_analysis.binaries,
        gui_analysis.datas,
        strip=False,
        upx=False,
        name="Phatch",
    )
