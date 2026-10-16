"""Output: stable JSON for agents, compact rich tables for humans."""

import dataclasses
import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from manaba_cli.models import Course

console = Console()
error_console = Console(stderr=True)

_FLAG_LABELS = {
    "unread_news": "news",
    "unsubmitted_tasks": "tasks",
    "new_grades": "grades",
    "unread_threads": "threads",
    "individual_messages": "messages",
}


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses, datetimes (ISO 8601), enums and paths into JSON-ready values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value


def print_json(value: Any) -> None:
    typer.echo(json.dumps(to_jsonable(value), ensure_ascii=False, indent=2))


def print_fields(fields: dict[str, Any]) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column()
    for key, value in fields.items():
        table.add_row(key, Text(format_value(value)))
    console.print(table)


def print_courses(courses: Sequence[Course]) -> None:
    _print_table(
        ("ID", "Course", "Year", "Period", "Teacher", "Alerts"),
        ((c.id, c.name, c.year, c.period, c.teacher, _flag_labels(c)) for c in courses),
    )


def format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def print_error(message: str) -> None:
    error_console.print(Text.assemble(("error: ", "red"), message))


def _print_table(columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    table = Table(box=box.SIMPLE_HEAD)
    for column in columns:
        table.add_column(column)
    for row in rows:
        # Text() keeps manaba titles like "[L2]" from being read as rich markup.
        table.add_row(*(Text(format_value(value)) for value in row))
    console.print(table)


def _flag_labels(course: Course) -> str | None:
    flags = dataclasses.asdict(course.flags)
    return ", ".join(label for flag, label in _FLAG_LABELS.items() if flags[flag]) or None
