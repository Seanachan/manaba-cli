from manaba_cli.models import Link, Page, PageDump
from manaba_cli.parsers.generic import parse_generic_page
from tests.support import BASE, fixture

RESULT_URL = f"{BASE}/ct/course_1001_drill_2002_submitlog_9001"


def test_dumps_main_column_with_answers_and_links() -> None:
    page = Page(url=RESULT_URL, html=fixture("drill_result.html"))

    assert parse_generic_page(page) == PageDump(
        url=RESULT_URL,
        title="【Unit 2　Review】Particles",
        text=(
            "【Unit 2　Review】Particles\n"
            "Part1 Choose one.\n"
            "1. Sample question 【＿】 one.\n"
            "( ) に\n"
            "(x) で\n"
            "○\n"
            "Part2 Fill in.\n"
            "1. Sample blank [に] two.\n"
            "Tests >>Plain Text"
        ),
        links=(Link(text="Tests", url=f"{BASE}/ct/course_1001_query"),),
    )


def test_falls_back_to_body_and_html_title() -> None:
    html = "<html><head><title>manaba</title></head><body><p>Hello</p></body></html>"

    dump = parse_generic_page(Page(url=f"{BASE}/ct/home", html=html))

    assert (dump.title, dump.text) == ("manaba", "Hello")
