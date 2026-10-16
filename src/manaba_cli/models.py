"""Domain records produced by the parsers. Field names are the stable JSON keys."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TaskKind(StrEnum):
    QUERY = "query"
    DRILL = "drill"
    REPORT = "report"
    SURVEY = "survey"


class TaskStatus(StrEnum):
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"


class SubmissionStatus(StrEnum):
    UNSUBMITTED = "unsubmitted"
    SUBMITTED = "submitted"
    PASSED = "passed"
    UNPASSED = "unpassed"


@dataclass(frozen=True)
class CourseFlags:
    """The status icons manaba shows next to each course."""

    unread_news: bool
    unsubmitted_tasks: bool
    new_grades: bool
    unread_threads: bool
    individual_messages: bool


@dataclass(frozen=True)
class Course:
    id: int
    name: str
    year: int | None
    period: str | None
    teacher: str | None
    url: str
    flags: CourseFlags


@dataclass(frozen=True)
class Task:
    course_id: int
    course_name: str | None
    kind: TaskKind
    id: int
    title: str
    status: TaskStatus | None
    my_status: SubmissionStatus | None
    status_raw: str
    start: datetime | None
    deadline: datetime | None
    url: str


@dataclass(frozen=True)
class Attachment:
    name: str
    uploaded_at: datetime | None
    url: str


@dataclass(frozen=True)
class NewsItem:
    course_id: int
    course_name: str | None
    id: int
    title: str
    author: str | None
    posted_at: datetime | None
    unread: bool
    url: str


@dataclass(frozen=True)
class NewsArticle:
    course_id: int
    course_name: str | None
    id: int
    title: str
    author: str | None
    posted_at: datetime | None
    url: str
    body: str
    attachments: tuple[Attachment, ...]


@dataclass(frozen=True)
class ContentPage:
    title: str
    author: str | None
    updated_at: datetime | None
    publish_start: datetime | None
    publish_end: datetime | None
    url: str
    text: str
    attachments: tuple[Attachment, ...]


@dataclass(frozen=True)
class Content:
    """A contents folder ("コンテンツ") of a course, holding one or more pages."""

    id: str
    title: str
    description: str | None
    updated_at: datetime | None
    url: str
    pages: tuple[ContentPage, ...] = ()


@dataclass(frozen=True)
class Link:
    text: str
    url: str


@dataclass(frozen=True)
class PageDump:
    """Generic text view of any manaba page, for ``manaba show``."""

    url: str
    title: str
    text: str
    links: tuple[Link, ...]
