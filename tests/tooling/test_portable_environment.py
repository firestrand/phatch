from __future__ import annotations

from pathlib import Path

from scripts import portable_smoke


def test_portable_smoke_poisons_all_platform_storage_and_observes_portable_state(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a complete portable layout and observable console/GUI boundaries
    root = tmp_path / "Phatch"
    portable_data = root / "portable-data"
    portable_data.mkdir(parents=True)
    existing_state = portable_data / "config" / "existing.json"
    existing_state.parent.mkdir()
    existing_state.write_text('{"existing": true}', encoding="utf-8")
    (root / "Phatch.exe").write_bytes(b"exe")
    (root / "Phatch-GUI.exe").write_bytes(b"exe")
    observed_environment: dict[str, str] = {}
    observed_portable_state: list[bool] = []

    def console(root: Path, work: Path, environment: dict[str, str]) -> None:
        del work
        observed_environment.update(environment)
        state = root / "portable-data" / "config" / "state.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{}", encoding="utf-8")
        logs = root / "portable-data" / "cache" / "logs"
        logs.mkdir(parents=True)
        (logs / "phatch.log").write_text("portable smoke passed", encoding="utf-8")

    def gui(root: Path, work: Path, environment: dict[str, str]) -> None:
        del work, environment
        observed_portable_state.append(
            (root / "portable-data" / "config" / "state.json").is_file()
        )

    monkeypatch.setattr(portable_smoke, "_exercise_console", console)
    monkeypatch.setattr(portable_smoke, "_exercise_gui", gui)

    # When: the portable smoke executes
    result = portable_smoke.main((str(root),))

    # Then: every native storage root is poisoned and portable state was created
    poisoned = {
        name: Path(observed_environment[name])
        for name in (
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "XDG_STATE_HOME",
        )
    }
    assert result == 0
    assert len(set(poisoned.values())) == len(poisoned)
    assert not any(path.exists() for path in poisoned.values())
    assert observed_portable_state == [True]
    assert existing_state.read_text(encoding="utf-8") == '{"existing": true}'
