"""Output: stable JSON for agents, compact rich tables for humans."""

import dataclasses
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


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
        table.add_row(key, format_value(value))
    console.print(table)


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
    error_console.print(f"[red]error:[/red] {message}", highlight=False, markup=True)
