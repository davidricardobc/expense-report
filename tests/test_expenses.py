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


def exp(amount: str, currency: str) -> Expense:
    return Expense(date(2026, 10, 3), "Item", Decimal(amount), currency)


class Totals(unittest.TestCase):
    def test_totals_sum_per_currency(self) -> None:
        lines = totals_by_currency([exp("10", "EUR"), exp("5", "EUR"), exp("7", "USD")]).split("\n")
        self.assertEqual(lines, ["EUR 15", "USD 7"])

    def test_totals_sorted_by_currency_code(self) -> None:
        lines = totals_by_currency([exp("1", "USD"), exp("1", "EUR"), exp("1", "COP")]).split("\n")
        self.assertEqual([line[:3] for line in lines], ["COP", "EUR", "USD"])

    def test_totals_format_two_decimals(self) -> None:
        self.assertEqual(totals_by_currency([exp("100", "EUR"), exp("41.90", "EUR")]), "EUR 141.90")

    def test_totals_of_nothing(self) -> None:
        self.assertEqual(totals_by_currency([]), "")


class Cli(unittest.TestCase):
    def test_prints_totals_after_summary(self) -> None:
        path = write_csv("date,description,amount,currency\n2026-10-03,A,5.50,usd\n2026-10-04,B,1.00,eur\n")
        out = subprocess.run([sys.executable, "-m", "report", str(path)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = out.stdout.splitlines()
        self.assertTrue(lines[0].startswith("2 expenses from"))
        self.assertEqual(lines[1:], ["EUR 1.00", "USD 5.50"])

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
