import subprocess
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from report.expenses import Expense, ReportError, parse_row, read_expenses, summary, totals_by_currency

ROW = {"date": "2026-10-03", "description": "Taxi", "amount": "12.50", "currency": "usd"}


def write_csv(text: str) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return Path(f.name)


class ParseRow(unittest.TestCase):
    def test_reads_a_row(self) -> None:
        self.assertEqual(parse_row(ROW, 2), Expense(date(2026, 10, 3), "Taxi", Decimal("12.50"), "USD"))

    def test_bad_date_names_the_line(self) -> None:
        with self.assertRaisesRegex(ReportError, "line 7"):
            parse_row({**ROW, "date": "03/10/2026"}, 7)

    def test_bad_amount(self) -> None:
        with self.assertRaises(ReportError):
            parse_row({**ROW, "amount": "twelve"}, 2)

    def test_bad_currency(self) -> None:
        with self.assertRaisesRegex(ReportError, "3-letter"):
            parse_row({**ROW, "currency": "dollars"}, 2)


class ReadAndSummarise(unittest.TestCase):
    def test_reads_a_file(self) -> None:
        path = write_csv("date,description,amount,currency\n2026-10-03,Taxi,12.50,USD\n2026-10-05,Lunch,9,EUR\n")
        self.assertEqual([e.currency for e in read_expenses(path)], ["USD", "EUR"])

    def test_error_line_counts_the_header(self) -> None:
        path = write_csv("date,description,amount,currency\n2026-10-03,Taxi,x,USD\n")
        with self.assertRaisesRegex(ReportError, "line 2"):
            read_expenses(path)

    def test_summary(self) -> None:
        expenses = [parse_row(ROW, 2), parse_row({**ROW, "date": "2026-09-30"}, 3)]
        self.assertEqual(summary(expenses), "2 expenses from 2026-09-30 to 2026-10-03")

    def test_summary_of_nothing(self) -> None:
        self.assertEqual(summary([]), "No expenses.")


class Totals(unittest.TestCase):
    def test_totals_sum_each_currency(self) -> None:
        expenses = [
            parse_row({**ROW, "amount": "100", "currency": "eur"}, 2),
            parse_row({**ROW, "amount": "5.50", "currency": "usd"}, 3),
            parse_row({**ROW, "amount": "41.90", "currency": "EUR"}, 4),
        ]
        self.assertEqual(totals_by_currency(expenses), {"EUR": Decimal("141.90"), "USD": Decimal("5.50")})

    def test_totals_are_ordered_by_currency_code(self) -> None:
        expenses = [parse_row({**ROW, "currency": c}, 2) for c in ("USD", "EUR", "COP")]
        self.assertEqual(list(totals_by_currency(expenses)), ["COP", "EUR", "USD"])

    def test_totals_of_nothing(self) -> None:
        self.assertEqual(totals_by_currency([]), {})


class Cli(unittest.TestCase):
    def test_cli_prints_a_line_per_currency(self) -> None:
        path = write_csv(
            "date,description,amount,currency\n"
            "2026-10-03,Taxi,12.50,USD\n"
            "2026-10-05,Lunch,100,EUR\n"
            "2026-10-06,Dinner,41.9,EUR\n"
        )
        out = self.run_cli(str(path))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(
            out.stdout.splitlines()[1:], ["EUR 141.90", "USD 12.50"]
        )
        self.assertIn("expenses from", out.stdout.splitlines()[0])

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "report", *args], capture_output=True, text=True)

    def test_prints_the_summary(self) -> None:
        out = self.run_cli("data/sample.csv")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("expenses from", out.stdout)

    def test_bad_file_exits_1(self) -> None:
        self.assertEqual(self.run_cli("missing.csv").returncode, 1)


if __name__ == "__main__":
    unittest.main()
