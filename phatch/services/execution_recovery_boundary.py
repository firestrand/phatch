from __future__ import annotations

from pathlib import Path

from phatch.core.execution_ports import Photo, Recovery, RecoveryAttempt
from phatch.core.execution_types import ExecutionIssue, ReportFile
from phatch.services.recovery_outcomes import RecoveryFinishResult


class MissingRecoveryAttemptError(RuntimeError):
    pass


class SourceRecoveryBoundary:
    __slots__ = ("attempt", "cancelled", "photo", "reports", "source")

    def __init__(self, source: Path) -> None:
        self.source = source
        self.attempt: RecoveryAttempt | None = None
        self.cancelled = False
        self.photo: Photo | None = None
        self.reports: tuple[ReportFile, ...] = ()

    def begin(self, recovery: Recovery) -> RecoveryAttempt:
        self.attempt = recovery.begin(self.source)
        return self.attempt

    def attach(self, photo: Photo) -> None:
        self.photo = photo

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        attempt = self.attempt
        if attempt is None:
            return
        try:
            attempt.fail(issues)
        finally:
            self.attempt = None

    def abort(self) -> None:
        attempt = self.attempt
        if attempt is None:
            return
        try:
            attempt.abort()
        finally:
            self.attempt = None

    def finish(self, issues: tuple[ExecutionIssue, ...]) -> RecoveryFinishResult:
        attempt = self.attempt
        if attempt is None:
            raise MissingRecoveryAttemptError("recovery attempt is required")
        result = attempt.finish(self.reports, issues)
        self.attempt = None
        return result

    def cleanup(self) -> tuple[OSError | KeyboardInterrupt, ...]:
        failures: list[OSError | KeyboardInterrupt] = []
        if self.photo is not None:
            try:
                self.photo.close()
            except (OSError, KeyboardInterrupt) as error:
                failures.append(error)
            self.photo = None
        try:
            self.abort()
        except (OSError, KeyboardInterrupt) as error:
            failures.append(error)
        return tuple(failures)
