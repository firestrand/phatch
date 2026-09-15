from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from phatch.core.execution_ports import RecoveryAttempt
from phatch.core.execution_types import OutputRecord, ReportFile, RollbackState
from phatch.services.output_transaction import (
    DeferredOutputTransaction,
    NoMetadataProvider,
    OutputRequest,
    PillowValidator,
)
from phatch.services.parallel_image_jobs import ImageJobSuccess
from phatch.services.recovery_outcomes import (
    RecoveryFinishFailed,
    RecoveryFinishResult,
    recovery_finish_result,
)


@dataclass(frozen=True, slots=True)
class CopyPreparedImage:
    source: Path

    def __call__(self, destination: Path) -> None:
        shutil.copyfile(self.source, destination)


def commit_image(
    success: ImageJobSuccess,
    report: ReportFile,
    attempt: RecoveryAttempt | None,
) -> RecoveryFinishResult:
    transaction = (
        attempt.transaction if attempt is not None else DeferredOutputTransaction()
    )
    try:
        success.destination.parent.mkdir(parents=True, exist_ok=True)
        transaction.execute(
            OutputRequest(
                success.destination,
                CopyPreparedImage(success.stage),
                NoMetadataProvider(),
                PillowValidator(
                    success.format_name,
                    (success.width, success.height),
                ),
            )
        )
    except (OSError, KeyboardInterrupt) as error:
        cleanup_errors: tuple[OSError | KeyboardInterrupt, ...] = ()
        try:
            transaction.discard()
        except (OSError, KeyboardInterrupt) as cleanup_error:
            cleanup_errors = (cleanup_error,)
        return RecoveryFinishFailed(
            error,
            (OutputRecord(report, survived=False),),
            RollbackState.COMPLETED,
            cleanup_errors,
        )
    if attempt is not None:
        return attempt.finish((report,), ())
    return recovery_finish_result(transaction.publish_all(), (report,))
