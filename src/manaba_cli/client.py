"""Read operations: fetch manaba pages through the session and parse them."""

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from manaba_cli.errors import ParseError
from manaba_cli.models import Content, Course, NewsArticle, NewsItem, Page, PageDump, Task
from manaba_cli.parsers.account import parse_screen_name
from manaba_cli.parsers.contents import (
    contents_list_ref,
    parse_content_page,
    parse_content_page_urls,
    parse_contents_list,
)
from manaba_cli.parsers.courses import COURSE_LIST_PAGE, parse_courses
from manaba_cli.parsers.generic import parse_generic_page
from manaba_cli.parsers.news import news_list_ref, parse_news_article, parse_news_list
from manaba_cli.parsers.tasks import TASK_LIST_PAGES, parse_task_list, task_list_ref
from manaba_cli.session import ManabaSession
from manaba_cli.urls import HOME_PAGE

# Be gentle with the university's server.
MAX_PARALLEL_REQUESTS = 4


class ManabaClient:
    def __init__(self, session: ManabaSession) -> None:
        self._session = session

    def screen_name(self) -> str | None:
        """The logged-in user's name as manaba shows it."""
        return self._read(HOME_PAGE, parse_screen_name)

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

    def contents(self, course_id: int) -> list[Content]:
        """Content folders of a course, each with the full text of its pages."""
        folders = self._read(contents_list_ref(course_id), parse_contents_list)
        return self._in_parallel(self._with_pages, folders)

    def page(self, ref: str) -> PageDump:
        """Any manaba page as text and links."""
        return self._read(ref, parse_generic_page)

    def _with_pages(self, folder: Content) -> Content:
        # Sequential within a folder: folders already run in parallel.
        page_urls = self._read(folder.url, parse_content_page_urls)
        pages = tuple(self._read(url, parse_content_page) for url in page_urls)
        return replace(folder, pages=pages)

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
