"""Read operations: fetch manaba pages through the session and parse them."""

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor

from manaba_cli.errors import ParseError
from manaba_cli.models import Course, Page
from manaba_cli.parsers.courses import COURSE_LIST_PAGE, parse_courses
from manaba_cli.session import ManabaSession

# Be gentle with the university's server.
MAX_PARALLEL_REQUESTS = 4


class ManabaClient:
    def __init__(self, session: ManabaSession) -> None:
        self._session = session

    def courses(self) -> list[Course]:
        return self._read(COURSE_LIST_PAGE, parse_courses)

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
