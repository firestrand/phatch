from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from tests.native_interaction_guard import (
    install_native_interaction_guard,
    run_bounded_main_loop,
)

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="native Windows GUI")


def test_native_windows_gui_loads_saves_preflights_and_processes(
    initialized_runtime,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: real wx, the initialized registry, and a safe generated image workflow
    from phatch.core import config, settings
    from phatch.pyWx import gui
    from phatch.services.action_schema_types import ActionDocument
    from phatch.services.preflight import PreflightRequest

    action_list = tmp_path / "GUI actions Ω.phatch"
    saved_copy = tmp_path / "GUI saved copy Ω.phatch"
    image = tmp_path / "GUI input Ω.png"
    output = tmp_path / "GUI output Ω"
    action_list.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "native GUI smoke",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "png",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    Image.new("RGB", (2, 2), "navy").save(image)
    # When: the actual application creates its main frame and round-trips the list
    observed: list[str] = []
    wx_app = gui.App(settings.create_settings(config.PATHS), str(action_list), 0)
    install_native_interaction_guard(monkeypatch)

    def inspect_and_close() -> None:
        frame = wx_app.GetTopWindow()
        assert isinstance(frame, gui.Frame)
        frame._open(str(action_list))
        loaded_actions = tuple(frame.controller.export_actions())
        assert loaded_actions
        document = ActionDocument.from_values(
            "native GUI smoke",
            (
                (
                    "save",
                    (
                        ("in", str(output)),
                        ("file_name", "<filename>"),
                        ("as", "png"),
                        ("metadata", "no"),
                        ("resolution", "72"),
                    ),
                ),
            ),
        )
        preflight = frame.controller.preflight(PreflightRequest(document, (image,), ()))
        assert preflight.estimated_work == 1
        frame._save(str(saved_copy))
        frame._open(str(saved_copy))
        frame._execute(tuple(frame.controller.export_actions()), paths=[str(image)])
        observed.append(frame.GetTitle())
        frame.Close()

    run_bounded_main_loop(wx_app, inspect_and_close, timeout_ms=30_000)

    # Then: both automation boundaries and the real main-frame lifecycle succeed
    assert output.joinpath("GUI input Ω.png").is_file()
    assert saved_copy.is_file()
    assert observed
    assert not Path(config.USER_LOG_PATH).is_file()
