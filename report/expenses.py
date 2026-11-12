"""Read expenses (date,description,amount,currency) from a CSV, JSON or XML file and summarise them."""

from __future__ import annotations

import csv
import json
from xml.etree import ElementTree
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass(frozen=True)
class Expense:
    day: date
    description: str
    amount: Decimal
    currency: str


class ReportError(ValueError):
    """A row the report cannot use; the message names its line in the file."""


def parse_row(row: dict[str, str], line: int) -> Expense:
    try:
        day = date.fromisoformat(row["date"].strip())
        amount = Decimal(row["amount"].strip())
    except (KeyError, AttributeError, ValueError, InvalidOperation) as exc:
        raise ReportError(f"line {line}: cannot read date or amount ({exc})") from exc
    currency = (row.get("currency") or "").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ReportError(f"line {line}: currency must be a 3-letter code, got {currency!r}")
    return Expense(day, (row.get("description") or "").strip(), amount, currency)


FIELDS = ("date", "description", "amount", "currency")


def _read_csv(path: Path) -> list[Expense]:
    with path.open(newline="", encoding="utf-8") as f:
        return [parse_row(row, n) for n, row in enumerate(csv.DictReader(f), start=2)]


def _read_json(path: Path) -> list[Expense]:
    try:
        with path.open(encoding="utf-8") as f:
            records = json.load(f, parse_float=str)
    except ValueError as exc:
        raise ReportError(f"invalid JSON ({exc})") from exc
    if not isinstance(records, list):
        raise ReportError("JSON must be a top-level array of objects")
    expenses = []
    for n, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            raise ReportError(f"line {n}: record must be an object")
        row = {k: str(v) for k, v in rec.items() if v is not None and not isinstance(v, (dict, list))}
        expenses.append(parse_row(row, n))
    return expenses


def _read_xml(path: Path) -> list[Expense]:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise ReportError(f"invalid XML ({exc})") from exc
    expenses = []
    for n, item in enumerate(root.findall("expense"), start=1):
        row = {k: item.findtext(k) for k in FIELDS if item.find(k) is not None}
        expenses.append(parse_row(row, n))
    return expenses


READERS = {".csv": _read_csv, ".json": _read_json, ".xml": _read_xml}


def read_expenses(path: Path) -> list[Expense]:
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise ReportError(f"unsupported file format {path.suffix!r} (use .csv, .json or .xml)")
    return reader(path)


def summary(expenses: list[Expense]) -> str:
    if not expenses:
        return "No expenses."
    days = sorted(e.day for e in expenses)
    return f"{len(expenses)} expenses from {days[0].isoformat()} to {days[-1].isoformat()}"
