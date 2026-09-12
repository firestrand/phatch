from __future__ import annotations

import multiprocessing
import os
import sys
from dataclasses import dataclass
from importlib import util
from pathlib import Path
from typing import Final

from . import app
from .core import config
from .core.resource_config import packaged_config_paths
from .pyWx.documentation import GuiModule, packaged_gui_help
from .resources.provider import ResourceProvider

GUI_EXTRA: Final = "Phatch[gui]"


@dataclass(frozen=True, slots=True)
class GuiDependencyError(ImportError):
    extra: str = GUI_EXTRA

    def __str__(self) -> str:
        return f"GUI support is unavailable; install {self.extra}"


def console_main() -> int:
    multiprocessing.freeze_support()
    configure_portable_data()
    from phatch.services.automation_cli import (
        is_automation_request,
        report_format_from_arguments,
        run_automation_cli,
    )

    arguments = tuple(sys.argv[1:])
    if is_automation_request(arguments):
        try:
            return run_automation_cli(arguments)
        except KeyboardInterrupt:
            from phatch.services.automation_report import write_failure
            from phatch.services.structured_report import AutomationOutcome

            report_format = report_format_from_arguments(arguments)
            return write_failure(
                AutomationOutcome.USER_CANCELLATION,
                "Cancelled by user.",
                report_format,
                sys.stdout,
                sys.stderr,
            )
    with packaged_config_paths() as resource_paths:
        app.main(
            config_paths=config.init_config_paths(resource_paths),
            force_console=True,
        )
    return 0


def gui_main() -> int:
    multiprocessing.freeze_support()
    configure_portable_data()
    try:
        gui_module = probe_gui()
    except GuiDependencyError as error:
        print(error, file=sys.stderr)
        return 1
    with (
        packaged_config_paths() as resource_paths,
        packaged_gui_help(gui_module, ResourceProvider()),
    ):
        app.main(config_paths=config.init_config_paths(resource_paths))
    return 0


def probe_gui() -> GuiModule:
    if util.find_spec("wx") is None:
        raise GuiDependencyError
    return app.import_pyWx()


def configure_portable_data() -> None:
    if not getattr(sys, "frozen", False):
        return
    portable_data = Path(sys.executable).resolve().parent / "portable-data"
    if not portable_data.is_dir():
        return
    os.environ["PHATCH_USER_CONFIG_DIR"] = str(portable_data / "config")
    os.environ["PHATCH_USER_DATA_DIR"] = str(portable_data / "data")
    os.environ["PHATCH_USER_CACHE_DIR"] = str(portable_data / "cache")
