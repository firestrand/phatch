# Phatch - Photo Batch Processor
# Copyright (C) 2007-2008 www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.
#
# Follows PEP8


import builtins
import sys

from rich.console import Console as RichConsole

from phatch.console.console import Frame as ConsoleFrame
from phatch.console.console import Progress, ask
from phatch.core import api, ct
from phatch.lib import formField, safe

_ = getattr(builtins, "_", str)


class Frame(ConsoleFrame):
    """Use existing console presentation with the reliable batch engine."""

    Progress = Progress

    def __init__(self, actionlist, paths, settings, output=sys.stdout):
        self.verbose = settings["verbose"] or settings["interactive"]
        self.settings = settings
        self.output = output
        self.console = RichConsole(file=output, highlight=False)
        self._pubsub()
        data, warning = api.open_batch_actionlist(self.verify_actionlist(actionlist))
        if formField.get_safe():
            if warning:
                raise safe.UnsafeError(warning)
        else:
            self.show_message(warning)
        settings["recipe_path"] = str(actionlist)
        self.result = api.apply_batch_actions_to_photos(
            data["actions"], settings, paths=paths
        )

    def append_save_action(self, actions):
        self.show_error(ct.SAVE_ACTION_NEEDED, exit=False)

    def verify_actionlist(self, actionlist):
        if actionlist or self.settings["interactive"]:
            return super().verify_actionlist(actionlist)
        raise ValueError("No action list provided")

    def show_progress_error(self, result, message, ignore=True):
        self.show_error(message, exit=False)
        if not self.settings["interactive"]:
            result["answer"] = _("stop")
            return
        result["stop_for_errors"] = True
        result["answer"] = ask(
            _("What do you want to do now?"), [_("abort"), _("skip"), _("ignore")]
        )


def main(actionlist, paths, settings, registry=None):
    import json

    from phatch.core.batch import BatchPlan
    from phatch.lib.atomic import AtomicOutput

    try:
        frame = Frame(actionlist, paths, settings)
        result = frame.result
    except (OSError, ValueError, KeyError, safe.UnsafeError) as exc:
        # Recipe/input setup failures have a stable status; no traceback payload.
        sys.stderr.write(f"Invalid batch setup: {type(exc).__name__}\n")
        from phatch.core.batch import BatchResult, Issue

        result = BatchResult(
            status="invalid_setup",
            issues=[Issue("invalid_recipe", "Recipe could not be loaded")],
        )
    if isinstance(result, BatchPlan):
        payload = result.to_dict(include_paths=settings.get("report_paths", False))
        status = 0 if result.valid else 2
        if not settings.get("report_path"):
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        payload = result.to_dict(include_paths=settings.get("report_paths", False))
        status = result.exit_code
    if settings.get("report_path"):
        from pathlib import Path

        report_path = Path(settings["report_path"]).expanduser().resolve()
        protected = {Path(actionlist).resolve()} if actionlist else set()
        if settings.get("manifest_path"):
            protected.add(Path(settings["manifest_path"]).expanduser().resolve())
        if hasattr(result, "reserved_paths"):
            protected.update(path.resolve() for path in result.reserved_paths)
        if isinstance(result, BatchPlan):
            protected.update(path.resolve() for path in result.resource_paths)
        for item in result.files:
            protected.add(item.source.resolve())
            if isinstance(result, BatchPlan):
                protected.update(dest.path.resolve() for dest in item.destinations)
            else:
                protected.update(output.resolve() for output in item.outputs)
                protected.update(output.resolve() for output in item.artifacts)
        for value in paths:
            candidate = Path(value).expanduser().resolve()
            protected.add(candidate)
            if (
                candidate.is_dir()
                and report_path.is_relative_to(candidate)
                and report_path.suffix.lstrip(".").lower() in settings["extensions"]
            ):
                protected.add(report_path)
        if report_path in protected:
            sys.stderr.write(
                "Report path overlaps a recipe, input or output; report not written.\n"
            )
            return 2
        with AtomicOutput(report_path) as temporary:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return status
