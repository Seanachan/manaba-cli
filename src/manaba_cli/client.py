"""Read operations: fetch manaba pages through the session and parse them."""

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from manaba_cli.errors import ParseError
from manaba_cli.models import Course, NewsArticle, NewsItem, Page, Task
from manaba_cli.parsers.courses import COURSE_LIST_PAGE, parse_courses
from manaba_cli.parsers.news import news_list_ref, parse_news_article, parse_news_list
from manaba_cli.parsers.tasks import TASK_LIST_PAGES, parse_task_list, task_list_ref
from manaba_cli.session import ManabaSession

# Be gentle with the university's server.
MAX_PARALLEL_REQUESTS = 4


class ManabaClient:
    def __init__(self, session: ManabaSession) -> None:
        self._session = session

    def courses(self) -> list[Course]:
        return self._read(COURSE_LIST_PAGE, parse_courses)

    def tasks(self, courses: Sequence[Course]) -> list[Task]:
        """Every task of ``courses``, read from each course's three task lists."""
        refs = [task_list_ref(c.id, list_page) for c in courses for list_page in TASK_LIST_PAGES]
        task_lists = self._in_parallel(lambda ref: self._read(ref, parse_task_list), refs)
        return _with_course_names(courses, task_lists)

    def news(self, courses: Sequence[Course]) -> list[NewsItem]:
        refs = [news_list_ref(course.id) for course in courses]
        news_lists = self._in_parallel(lambda ref: self._read(ref, parse_news_list), refs)
        return _with_course_names(courses, news_lists)

    def news_article(self, ref: str) -> NewsArticle:
        """One news article; reading it marks it as read on manaba, as in the browser."""
        return self._read(ref, parse_news_article)

    def _read[T](self, ref: str, parse: Callable[[Page], T]) -> T:
        page = self._session.get(ref)
        try:
            return parse(page)
        except ParseError as error:
            raise ParseError(str(error), url=page.url, html=page.html) from error

    @staticmethod
    def _in_parallel[S, T](work: Callable[[S], T], items: Iterable[S]) -> list[T]:
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as pool:
            return list(pool.map(work, items))


def _with_course_names[R: (Task, NewsItem)](
    courses: Sequence[Course], per_course: Iterable[list[R]]
) -> list[R]:
    """Flatten per-course lists, filling in the course name the list pages do not show."""
    names = {course.id: course.name for course in courses}
    return [
        replace(record, course_name=names.get(record.course_id))
        for records in per_course
        for record in records
    ]
