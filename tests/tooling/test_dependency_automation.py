from pathlib import Path
from typing import TypedDict, cast

import yaml

PROJECT_ROOT = Path(__file__).parents[2]
DEPENDABOT_PATH = PROJECT_ROOT / ".github" / "dependabot.yml"


class Schedule(TypedDict):
    timezone: str


Update = TypedDict(
    "Update",
    {
        "package-ecosystem": str,
        "directory": str,
        "schedule": Schedule,
        "groups": dict[str, dict[str, str | list[str]]],
    },
)


class DependabotConfiguration(TypedDict):
    version: int
    updates: list[Update]


def load_dependabot() -> DependabotConfiguration:
    document = yaml.safe_load(DEPENDABOT_PATH.read_text(encoding="utf-8"))
    return cast(DependabotConfiguration, document)


def test_dependabot_updates_locked_python_and_github_actions_dependencies() -> None:
    # Given: the repository dependency automation policy
    configuration = load_dependabot()

    # When: configured package ecosystems are selected
    updates = configuration["updates"]
    ecosystems = [update["package-ecosystem"] for update in updates]

    # Then: both locked Python dependencies and workflow actions are covered
    assert configuration["version"] == 2
    assert ecosystems == ["uv", "github-actions"]
    assert all(update["directory"] == "/" for update in updates)
    assert all(update["schedule"]["timezone"] == "Etc/UTC" for update in updates)


def test_dependabot_groups_reviews_and_excludes_native_image_updates() -> None:
    # Given: the uv update policy
    uv_updates = load_dependabot()["updates"][0]

    # When: groups and exclusions are inspected
    groups = uv_updates["groups"]
    production_group = groups["python-production"]

    # Then: routine updates are grouped while sensitive binaries remain manual
    assert groups == {
        "python-production": {
            "dependency-type": "production",
            "exclude-patterns": [
                "Pillow",
                "pillow-heif",
                "pyexiv2",
                "pywin32",
                "wxPython",
            ],
        },
        "python-development": {"dependency-type": "development"},
    }
    assert production_group["exclude-patterns"]
    assert "ignore" not in uv_updates
