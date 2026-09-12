import subprocess
import sys


IMPORT_GUARDS = """
import os
import subprocess
import sys
import tempfile

tempfile.tempdir = os.environ['TMPDIR']

def reject_process(*args, **kwargs):
    raise AssertionError('import started a process')

subprocess.Popen = reject_process
subprocess.run = reject_process
subprocess.call = reject_process
subprocess.check_call = reject_process
subprocess.check_output = reject_process
os.system = reject_process

try:
    import wx
except ImportError:
    pass
else:
    def reject_gui(*args, **kwargs):
        raise AssertionError('import constructed a GUI object')

    wx.App = reject_gui
    wx.Frame = reject_gui
    wx.Dialog = reject_gui

def reject_side_effects(event, args):
    if event in ('subprocess.Popen', 'os.system'):
        raise AssertionError('import started a process')
    if event != 'open':
        return
    _, mode, flags = args
    writes_by_mode = isinstance(mode, str) and any(
        marker in mode for marker in ('w', 'a', 'x', '+'))
    writes_by_flags = isinstance(flags, int) and bool(
        flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if writes_by_mode or writes_by_flags:
        raise AssertionError('import opened a file for writing')

sys.addaudithook(reject_side_effects)
"""


def run_import(isolated_runtime, statement):
    before = sorted(isolated_runtime.root.rglob('*'))
    result = subprocess.run(
        [sys.executable, '-c', IMPORT_GUARDS + statement],
        cwd=isolated_runtime.cwd,
        env=isolated_runtime.env,
        capture_output=True,
        text=True,
        check=False,
    )
    after = sorted(isolated_runtime.root.rglob('*'))
    return result, before, after


def test_importing_phatch_does_not_write_user_files_or_start_processes(
        isolated_runtime):
    result, before, after = run_import(isolated_runtime, '\nimport phatch\n')

    assert result.returncode == 0, result.stderr
    assert after == before


def test_importing_console_is_hermetic(isolated_runtime):
    result, before, after = run_import(
        isolated_runtime,
        '\nimport phatch.console.console\n',
    )

    assert result.returncode == 0, result.stderr
    assert after == before


def test_importing_every_action_is_hermetic(isolated_runtime):
    statement = """
import importlib
import pkgutil
import phatch.actions

for module in pkgutil.iter_modules(phatch.actions.__path__):
    importlib.import_module(f'phatch.actions.{module.name}')
"""
    result, before, after = run_import(isolated_runtime, statement)

    assert result.returncode == 0, result.stderr
    assert after == before
