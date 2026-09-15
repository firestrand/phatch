import tempfile
from pathlib import Path

from phatch.services.report_privacy import (
    ReportPrivacyContext,
    SensitiveRoot,
    privacy_for_cli_paths,
    privacy_for_paths,
    redact_path,
    redact_text,
)


def test_redaction_uses_longest_matching_root() -> None:
    privacy = ReportPrivacyContext(
        (
            SensitiveRoot(Path("/workspace"), "<workspace>"),
            SensitiveRoot(Path("/workspace/private"), "<input>"),
        )
    )

    assert redact_path(Path("/workspace/private/image.png"), privacy) == (
        "<input>/image.png"
    )


def test_redaction_requires_a_path_boundary() -> None:
    privacy = ReportPrivacyContext((SensitiveRoot(Path("/home/al"), "<home>"),))

    assert redact_text("/home/al/file.jpg", privacy) == "<home>/file.jpg"
    assert redact_text("/home/alice/file.jpg", privacy) == "/home/alice/file.jpg"


def test_redaction_removes_common_credential_shapes() -> None:
    privacy = ReportPrivacyContext(())
    diagnostic = (
        'Authorization: Bearer abc123 "token": "def456" '
        "password: hunter2 api_key=key789 "
        "https://user:url-secret@example.test GPS=51.0"
    )

    redacted = redact_text(diagnostic, privacy)

    for secret in (
        "abc123",
        "def456",
        "hunter2",
        "key789",
        "user:url-secret",
        "51.0",
    ):
        assert secret not in redacted
    assert redacted.count("<redacted>") == 6


def test_default_privacy_redacts_the_runtime_temp_alias() -> None:
    temp_root = Path(tempfile.gettempdir()).absolute()

    redacted = redact_text(str(temp_root / "private.txt"), privacy_for_paths())

    assert redacted == "<temp>/private.txt"


def test_cli_privacy_labels_only_explicit_action_list_and_input_roots() -> None:
    action_list = Path("/Volumes/private-client/config/actions.phatch")
    input_path = Path("/Volumes/private-client/input/photo.jpg")
    privacy = privacy_for_cli_paths(action_list, (input_path,))

    diagnostic = (
        f"config={action_list}; input={input_path}; "
        "unknown=--foo/path; unrelated=/opt/public/tool"
    )

    assert redact_text(diagnostic, privacy) == (
        "config=<action-list>/actions.phatch; input=<input>/photo.jpg; "
        "unknown=--foo/path; unrelated=/opt/public/tool"
    )
