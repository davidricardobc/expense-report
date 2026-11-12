import subprocess
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from report.expenses import (Expense, ReportError, monthly_report, monthly_totals, parse_row,
                             read_expenses, summary)

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


def exp(day: str, amount: str, currency: str) -> Expense:
    return Expense(date.fromisoformat(day), "x", Decimal(amount), currency)


class Monthly(unittest.TestCase):
    def test_sums_per_currency_within_a_month(self) -> None:
        got = monthly_totals([exp("2026-10-03", "12.50", "USD"), exp("2026-10-09", "7.25", "USD"),
                              exp("2026-10-05", "9", "EUR")])
        self.assertEqual(got, {"2026-10": {"USD": Decimal("19.75"), "EUR": Decimal("9")}})

    def test_splits_on_month_boundary(self) -> None:
        got = monthly_totals([exp("2026-09-30", "1", "USD"), exp("2026-10-01", "2", "USD")])
        self.assertEqual(sorted(got), ["2026-09", "2026-10"])

    def test_report_is_chronological_with_sorted_currencies(self) -> None:
        text = monthly_report([exp("2026-10-01", "12.50", "USD"), exp("2026-09-30", "9.00", "EUR"),
                               exp("2026-10-02", "3", "EUR")])
        self.assertEqual(text, "2026-09\n  EUR 9.00\n2026-10\n  EUR 3\n  USD 12.50")

    def test_report_of_nothing(self) -> None:
        self.assertEqual(monthly_report([]), "No expenses.")


class Cli(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "report", *args], capture_output=True, text=True)

    def test_prints_the_summary(self) -> None:
        out = self.run_cli("data/sample.csv")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("expenses from", out.stdout)

    def test_by_month(self) -> None:
        path = write_csv("date,description,amount,currency\n2026-10-03,Taxi,12.50,USD\n")
        out = self.run_cli(str(path), "--by-month")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("2026-10\n  USD 12.50", out.stdout)

    def test_unknown_flag_exits_2(self) -> None:
        self.assertEqual(self.run_cli("data/sample.csv", "--nope").returncode, 2)

    def test_bad_file_exits_1(self) -> None:
        self.assertEqual(self.run_cli("missing.csv").returncode, 1)


if __name__ == "__main__":
    unittest.main()
