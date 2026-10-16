"""Task status words in manaba's Japanese and English UI.

manaba prints a task's state on the first line of the status cell and the user's own
progress on the following lines, e.g. ``In progress`` / ``Not submitted`` or
``受付終了`` / ``提出済み``. Unknown wording maps to None; callers keep the raw text.
"""

from collections.abc import Sequence

from manaba_cli.models import SubmissionStatus, TaskStatus

_TASK_STATUS_WORDS: Sequence[tuple[TaskStatus, tuple[str, ...]]] = (
    (TaskStatus.UPCOMING, ("受付開始待ち", "not started", "waiting")),
    (TaskStatus.OPEN, ("受付中", "in progress")),
    (TaskStatus.CLOSED, ("受付終了", "closed")),
)

# Checked in order: negative forms first, because "not submitted" contains "submitted"
# and "未合格" contains "合格".
_SUBMISSION_WORDS: Sequence[tuple[SubmissionStatus, tuple[str, ...]]] = (
    (SubmissionStatus.UNSUBMITTED, ("未提出", "まだ提出", "not submitted")),
    (SubmissionStatus.UNPASSED, ("未合格", "not passed")),
    (SubmissionStatus.PASSED, ("合格", "passed")),
    (SubmissionStatus.SUBMITTED, ("提出済", "submitted")),
)


def parse_task_status(line: str) -> TaskStatus | None:
    return _first_match(line, _TASK_STATUS_WORDS)


def parse_submission_status(lines: Sequence[str]) -> SubmissionStatus | None:
    return _first_match(" ".join(lines), _SUBMISSION_WORDS)


def _first_match[S](text: str, vocabulary: Sequence[tuple[S, tuple[str, ...]]]) -> S | None:
    lowered = text.lower()
    for status, words in vocabulary:
        if any(word in lowered for word in words):
            return status
    return None
