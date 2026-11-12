"""python3 -m report <file.csv>"""

from __future__ import annotations

import sys
from pathlib import Path

from report.expenses import ReportError, monthly_report, read_expenses, summary


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--by-month"]
    if len(args) != 1 or len(argv) - len(args) > 1 or args[0].startswith("--"):
        print("usage: python3 -m report <file.csv> [--by-month]", file=sys.stderr)
        return 2
    try:
        expenses = read_expenses(Path(args[0]))
    except (OSError, ReportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(monthly_report(expenses) if "--by-month" in argv else summary(expenses))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
