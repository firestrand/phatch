from __future__ import annotations

from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.resources.provider import LogicalResource
from phatch.services.preview_policy import (
    AdapterKind,
    AdapterRequirement,
    PolicyKind,
    PreviewPolicy,
    ReadCondition,
    ReadKind,
    ReadRequirement,
    policy_for,
)
from phatch.services.preview_types import (
    PackagedPreviewRead,
    PreviewActionSpec,
    PreviewAdmissionError,
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewFileFingerprint,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
    PreviewWorkerRequest,
    SelectedPreviewRead,
)
from phatch.services.preview_worker import (
    _execute,
    _materialize_fields,
    _validate_declared_reads,
    _validate_policies,
    _verify_fingerprint,
)


def _request(path: Path, action: PreviewActionSpec) -> PreviewWorkerRequest:
    source = PreviewSource(
        path,
        sha256(path.read_bytes()).hexdigest(),
        PreviewSize(4, 3),
        "RGB",
        "PNG",
    )
    spec = PreviewExecutionSpec(
        (action,),
        source,
        (),
        (),
        PreviewLimits(),
        PreviewReadContext(source, ()),
        False,
    )
    return PreviewWorkerRequest("branches", spec, ())


def test_worker_policy_recheck_rejects_blocked_action(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    request = _request(source, PreviewActionSpec("copy", ()))

    with pytest.raises(PreviewAdmissionError) as captured:
        _validate_policies(request)

    assert captured.value.code is PreviewErrorCode.BLOCKED_ACTION


def test_worker_materializes_selected_read(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    selected = tmp_path / "mark.png"
    for path in (source, selected):
        with Image.new("RGB", (4, 3)) as image:
            image.save(path)
    action = PreviewActionSpec("watermark", (("mark", "selected"),))
    request = _request(source, action)
    read = SelectedPreviewRead(
        0, "mark", selected, sha256(selected.read_bytes()).hexdigest()
    )
    request = PreviewWorkerRequest(
        request.request_id,
        PreviewExecutionSpec(
            request.spec.actions,
            request.spec.source,
            (read,),
            request.spec.required_variables,
            request.spec.limits,
            PreviewReadContext(request.spec.source, (read,)),
            False,
        ),
        (),
    )

    with ExitStack() as resources:
        fields = _materialize_fields(request, resources)
        materialized = Path(fields[0]["mark"])
        assert materialized != selected
        assert materialized.read_bytes() == selected.read_bytes()

    assert not materialized.exists()


def test_worker_read_recheck_handles_absent_adapter_field(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    request = _request(source, PreviewActionSpec("watermark", ()))

    with pytest.raises(PreviewAdmissionError) as captured:
        _validate_declared_reads(0, {}, policy_for("watermark"), request)

    assert captured.value.code is PreviewErrorCode.UNDECLARED_READ


def test_worker_read_recheck_requires_declared_present_adapter_field(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    request = _request(source, PreviewActionSpec("watermark", (("mark", "selected"),)))

    with pytest.raises(PreviewAdmissionError) as captured:
        _validate_declared_reads(
            0,
            {"mark": "selected"},
            policy_for("watermark"),
            request,
        )

    assert captured.value.code is PreviewErrorCode.UNDECLARED_READ


def test_worker_reports_missing_fingerprint_source(tmp_path: Path) -> None:
    missing = tmp_path / "missing.png"

    with pytest.raises(PreviewAdmissionError) as captured:
        _verify_fingerprint(missing, "unused")

    assert captured.value.code is PreviewErrorCode.SOURCE_CHANGED


def test_worker_rechecks_selected_file_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    selected = tmp_path / "selected.png"
    for path in (source, selected):
        with Image.new("RGB", (4, 3)) as image:
            image.save(path)
    request = _request(source, PreviewActionSpec("scale", ()))
    stale = PreviewFileFingerprint(selected, "stale")
    request = PreviewWorkerRequest(request.request_id, request.spec, (stale,))

    with pytest.raises(PreviewAdmissionError) as captured:
        _execute(request)

    assert captured.value.code is PreviewErrorCode.SOURCE_CHANGED


def test_worker_read_recheck_honors_conditions_and_background_adapter(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    request = _request(source, PreviewActionSpec("background", ()))
    policy = PreviewPolicy(
        "background",
        PolicyKind.ELIGIBLE,
        reads=(
            ReadRequirement(
                "optional",
                ReadKind.PACKAGED_OR_SELECTED_FILE,
                ReadCondition("mode", "Image"),
            ),
        ),
        adapters=(AdapterRequirement("mark", AdapterKind.FILE_REFERENCE),),
    )

    _validate_declared_reads(
        0, {"mode": "Color", "fill": "Color", "mark": "unused"}, policy, request
    )


def test_worker_materializes_packaged_file_and_skips_catalog(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    action = PreviewActionSpec("watermark", (("mark", "Watermark"),))
    request = _request(source, action)
    reads = (
        PackagedPreviewRead(
            0, "mark", LogicalResource.parse("data/actionlists/watermark.png")
        ),
    )
    request = PreviewWorkerRequest(
        request.request_id,
        PreviewExecutionSpec(
            request.spec.actions,
            request.spec.source,
            reads,
            request.spec.required_variables,
            request.spec.limits,
            PreviewReadContext(request.spec.source, reads),
            False,
        ),
        (),
    )

    with ExitStack() as resources:
        fields = _materialize_fields(request, resources)
        assert Path(fields[0]["mark"]).is_file()


def test_worker_keeps_packaged_catalog_value_for_action_adapter(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    with Image.new("RGB", (4, 3)) as image:
        image.save(source)
    action = PreviewActionSpec("perspective", (("projection", "4x4"),))
    request = _request(source, action)
    read = PackagedPreviewRead(
        0,
        "projection",
        LogicalResource.parse("data/perspective/4x4.txt"),
    )
    request = PreviewWorkerRequest(
        request.request_id,
        PreviewExecutionSpec(
            request.spec.actions,
            request.spec.source,
            (read,),
            request.spec.required_variables,
            request.spec.limits,
            PreviewReadContext(request.spec.source, (read,)),
            False,
        ),
        (),
    )

    with ExitStack() as resources:
        fields = _materialize_fields(request, resources)

    assert fields[0]["projection"] == "4x4"
