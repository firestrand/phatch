from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from phatch.core.execution_ports import Photo
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionIssue,
    ExecutionPosition,
    IssueSeverity,
    IssueStage,
    ReportFile,
)
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyImage,
    LegacyImageInfo,
    LegacyPhotoObject,
)
from phatch.services.legacy_types import (
    translate as _,
)


@dataclass(slots=True)
class LegacyPhotoState:
    image_infos: dict[Path, deque[LegacyImageInfo]] = field(
        default_factory=lambda: defaultdict(deque)
    )
    valid_infos: list[LegacyImageInfo] = field(default_factory=list)
    invalid_infos: list[LegacyImageInfo] = field(default_factory=list)
    report: list[Mapping[str, object]] = field(default_factory=list)
    info_not_file: object | None = None
    verification_cancelled: bool = False

    def add(self, source: DiscoveredFile, info: LegacyImageInfo) -> None:
        self.image_infos[source.path].append(info)

    def peek(self, source: DiscoveredFile) -> LegacyImageInfo:
        return self.image_infos[source.path][0]

    def take(self, source: DiscoveredFile) -> LegacyImageInfo:
        return self.image_infos[source.path].popleft()


@dataclass(slots=True)
class LegacyPhotoAdapter:
    source: DiscoveredFile
    photo: LegacyPhotoObject
    state: LegacyPhotoState
    _original_image: LegacyImage = field(init=False)
    _reported_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        original_image = self.photo.get_layer().image
        assert original_image is not None
        self._original_image = original_image

    def set_position(self, position: ExecutionPosition) -> None:
        self.photo.info.set("imageindex", position.file_index)
        self.photo.info.set("index", position.item_index)
        self.photo.info.set("repeatindex", position.repeat_index)

    def prepare_repeat_image(self, repeat_index: int, repeat_count: int) -> None:
        layer = self.photo.get_layer()
        if repeat_index == repeat_count - 1:
            layer.image = self._original_image
        elif repeat_index > 0:
            layer.image = self._original_image.copy()

    def reports(self) -> tuple[ReportFile, ...]:
        self.state.report.extend(self.photo.report_files[self._reported_count :])
        self._reported_count = len(self.photo.report_files)
        reports: list[ReportFile] = []
        for raw in self.photo.report_files:
            path = Path(str(raw["path"]))
            source = Path(str(raw.get("source", self.source.path)))
            width = raw.get("width")
            height = raw.get("height")
            mode = raw.get("mode")
            if (
                isinstance(width, int)
                and isinstance(height, int)
                and isinstance(mode, str)
            ):
                reports.append(ReportFile(source, path, width, height, mode))
            else:
                reports.append(ReportFile(source, path))
        return tuple(reports)

    def set_output_transaction(self, transaction) -> None:
        self.photo.set_output_transaction(transaction)

    def close(self) -> None:
        self.photo.close()


class LegacyOpenInteraction(Protocol):
    def record_execution_error(
        self,
        photo: LegacyPhotoObject | None,
        issue: ExecutionIssue,
        action: LegacyActionObject | None,
        *,
        can_continue: bool,
    ) -> None: ...


@dataclass(slots=True)
class LegacyPhotoAccess:
    state: LegacyPhotoState
    interaction: LegacyOpenInteraction

    def verify(self, source: DiscoveredFile) -> bool:
        from phatch.core import api

        info = self.state.peek(source)
        result: dict[str, object] = {}
        api.send.progress_update_filename(
            result,
            len(self.state.valid_infos),
            str(source.path),
        )
        if result and not bool(result["keepgoing"]):
            self.state.verification_cancelled = True
            self.state.invalid_infos.append(info)
            return False
        valid: list[LegacyImageInfo] = []
        invalid: list[LegacyImageInfo] = []
        api.openImage.verify_image(info, valid, invalid)
        self.state.valid_infos.extend(valid)
        self.state.invalid_infos.extend(invalid)
        return bool(valid)

    def open(
        self,
        source: DiscoveredFile,
        required_variables: tuple[str, ...],
    ) -> Photo | ExecutionIssue:
        from phatch.core import api

        info = self.state.take(source)
        try:
            photo = api.pil.Photo(info, self.state.info_not_file)
        except Exception as error:
            message = (
                f"{_('Unable to open file')}: {info['path']}:\n"
                f"{api.exception_to_unicode(error)}"
            )
            issue = ExecutionIssue(
                IssueStage.PHOTO_OPEN,
                IssueSeverity.ERROR,
                message,
                source.path,
            )
            self.interaction.record_execution_error(
                None,
                issue,
                None,
                can_continue=False,
            )
            return issue
        return LegacyPhotoAdapter(source, photo, self.state)
