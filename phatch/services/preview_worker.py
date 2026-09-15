from __future__ import annotations

import io
import os
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from PIL import Image

from phatch.core import pil
from phatch.lib import metadata
from phatch.resources.provider import ResourceProvider
from phatch.services.preview_actions import construct_preview_actions
from phatch.services.preview_dimensions import predict_preview_size
from phatch.services.preview_inspection import validate_preview_transition
from phatch.services.preview_policy import (
    AdapterKind,
    PolicyKind,
    PreviewPolicy,
    policy_for,
)
from phatch.services.preview_read_snapshot import (
    snapshot_selected_read,
    snapshot_verified_file,
)
from phatch.services.preview_types import (
    PackagedPreviewRead,
    PreviewAdmissionError,
    PreviewErrorCode,
    PreviewImagePayload,
    PreviewSize,
    PreviewWorkerFailure,
    PreviewWorkerRequest,
    PreviewWorkerResult,
    PreviewWorkerSuccess,
    SelectedPreviewRead,
)


class PreviewWorkerConnection(Protocol):
    def send(self, result: PreviewWorkerResult) -> None: ...

    def close(self) -> None: ...


class PreviewLayer(Protocol):
    image: Image.Image | None


def execute_preview_worker(
    request: PreviewWorkerRequest, connection: PreviewWorkerConnection
) -> None:
    try:
        result = _execute(request)
    except PreviewAdmissionError as error:
        result = PreviewWorkerFailure(
            request.request_id, error.code, error.reason, os.getpid()
        )
    except Exception as error:
        result = PreviewWorkerFailure(
            request.request_id,
            PreviewErrorCode.WORKER_FAILED,
            f"{type(error).__name__}: {error}",
            os.getpid(),
        )
    try:
        connection.send(result)
    finally:
        connection.close()


def _execute(request: PreviewWorkerRequest) -> PreviewWorkerSuccess:
    for selected in request.selected_files:
        _verify_fingerprint(selected.path, selected.sha256)
    _validate_policies(request)
    photo = None
    try:
        with ExitStack() as resources:
            source = request.spec.source
            source_path = resources.enter_context(
                snapshot_verified_file(source.path, source.sha256)
            )
            fields = _materialize_fields(request, resources)
            actions = construct_preview_actions(request.spec.actions, fields)
            info = metadata.InfoExtract(str(source_path), vars=pil.BASE_VARS).dump()
            requested_info = metadata.InfoExtract(
                vars=list(request.spec.required_variables)
            )
            photo = pil.Photo(info, requested_info)
            photo.info.update(dict(source.logical_file_info), explicit=False)
            settings: dict[str, object] = {}
            cache: dict[str, object] = {}
            for action_index, (action_spec, action) in enumerate(
                zip(request.spec.actions, actions, strict=True)
            ):
                policy = policy_for(action_spec.action_id)
                _validate_declared_reads(
                    action_index,
                    dict(action_spec.fields),
                    policy,
                    request,
                )
                before_image = _layer_image(photo.get_layer())
                before = PreviewSize(*before_image.size)
                predicted = predict_preview_size(
                    action_spec.action_id, action, photo.info, before
                )
                validate_preview_transition(
                    before, predicted, request.spec.limits.max_live_bytes
                )
                action.apply(photo, settings, cache)
                after_image = _layer_image(photo.get_layer())
                after = PreviewSize(*after_image.size)
                validate_preview_transition(
                    before, after, request.spec.limits.max_live_bytes
                )
            image = photo.get_flattened_image()
            try:
                validate_preview_transition(
                    request.spec.source.size,
                    PreviewSize(*image.size),
                    request.spec.limits.max_live_bytes,
                )
                payload = _encode(image)
            finally:
                image.close()
    finally:
        if photo is not None:
            for layer in photo.layers.values():
                if layer.image is not None:
                    layer.image.close()
            photo.close()
    return PreviewWorkerSuccess(request.request_id, payload, os.getpid())


def _validate_policies(request: PreviewWorkerRequest) -> None:
    for action_spec in request.spec.actions:
        policy = policy_for(action_spec.action_id)
        if policy.kind is not PolicyKind.ELIGIBLE:
            raise PreviewAdmissionError(
                PreviewErrorCode.BLOCKED_ACTION,
                "action is not eligible for preview execution",
                action_spec.action_id,
            )


def _layer_image(layer: PreviewLayer) -> Image.Image:
    image = layer.image
    if image is None:
        raise PreviewAdmissionError(
            PreviewErrorCode.WORKER_FAILED,
            "preview action produced no layer image",
        )
    return image


def _validate_declared_reads(
    action_index: int,
    fields: dict[str, str],
    policy: PreviewPolicy,
    request: PreviewWorkerRequest,
) -> None:
    declared = {(read.action_index, read.field_id) for read in request.spec.reads}
    required: set[str] = set()
    for read in policy.reads:
        condition = read.condition
        if condition is None or fields.get(condition.field_id) == condition.equals:
            required.add(read.field_id)
    for adapter in policy.adapters:
        if (
            policy.action_id == "background"
            and adapter.field_id == "mark"
            and fields.get("fill") != "Image"
        ):
            continue
        if adapter.field_id in fields:
            required.add(adapter.field_id)
    missing = sorted(
        field_id for field_id in required if (action_index, field_id) not in declared
    )
    if missing:
        raise PreviewAdmissionError(
            PreviewErrorCode.UNDECLARED_READ,
            f"undeclared preview reads: {', '.join(missing)}",
            policy.action_id,
        )


def _materialize_fields(
    request: PreviewWorkerRequest, resources: ExitStack
) -> tuple[dict[str, str], ...]:
    values = [dict(action.fields) for action in request.spec.actions]
    provider = ResourceProvider()
    for read in request.spec.reads:
        if isinstance(read, PackagedPreviewRead):
            policy = policy_for(request.spec.actions[read.action_index].action_id)
            if any(
                adapter.field_id == read.field_id
                and adapter.kind is AdapterKind.PACKAGED_CATALOG
                for adapter in policy.adapters
            ):
                continue
            path = resources.enter_context(provider.as_path(read.resource))
        elif isinstance(read, SelectedPreviewRead):
            path = resources.enter_context(snapshot_selected_read(read))
        else:
            continue
        values[read.action_index][read.field_id] = str(path)
    return tuple(values)


def _verify_fingerprint(path: Path, expected: str) -> None:
    digest = sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.SOURCE_CHANGED,
            f"preview input changed: {path}",
        ) from error
    if digest.hexdigest() != expected:
        raise PreviewAdmissionError(
            PreviewErrorCode.SOURCE_CHANGED, f"preview input changed: {path}"
        )


def _encode(image: Image.Image) -> PreviewImagePayload:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return PreviewImagePayload(
        output.getvalue(), image.width, image.height, image.mode, "PNG"
    )
