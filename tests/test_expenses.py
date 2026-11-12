import subprocess
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from report.expenses import Expense, ReportError, parse_row, read_expenses, summary

ROW = {"date": "2026-10-03", "description": "Taxi", "amount": "12.50", "currency": "usd"}


def write_file(text: str, suffix: str = ".csv") -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return Path(f.name)


def write_csv(text: str) -> Path:
    return write_file(text, ".csv")


def xml_expense(*fields: str) -> str:
    return "<expense>" + "".join(fields) + "</expense>"


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


JSON_TWO = (
    '[{"date": "2026-10-03", "description": "Taxi", "amount": "12.50", "currency": "usd"},'
    ' {"date": "2026-10-05", "description": "Lunch", "amount": 9, "currency": "EUR"}]'
)


class OtherFormats(unittest.TestCase):
    def test_reads_a_json_file(self) -> None:
        got = read_expenses(write_file(JSON_TWO, ".json"))
        self.assertEqual(got, [
            Expense(date(2026, 10, 3), "Taxi", Decimal("12.50"), "USD"),
            Expense(date(2026, 10, 5), "Lunch", Decimal("9"), "EUR"),
        ])

    def test_json_amount_stays_decimal(self) -> None:
        text = '[{"date": "2026-10-03", "description": "T", "amount": 12.50, "currency": "USD"}]'
        self.assertEqual(read_expenses(write_file(text, ".json"))[0].amount, Decimal("12.50"))

    def test_json_bad_record_names_the_line(self) -> None:
        text = JSON_TWO.replace('"amount": 9', '"amount": "x"')
        with self.assertRaisesRegex(ReportError, "line 2"):
            read_expenses(write_file(text, ".json"))

    def test_invalid_json_raises_report_error(self) -> None:
        with self.assertRaises(ReportError):
            read_expenses(write_file("[{oops", ".json"))

    def test_reads_an_xml_file(self) -> None:
        item = xml_expense(
            "<date>2026-10-03</date>", "<description>Taxi</description>",
            "<amount>12.50</amount>", "<currency>usd</currency>",
        )
        got = read_expenses(write_file(f"<expenses>{item}</expenses>", ".xml"))
        self.assertEqual(got, [Expense(date(2026, 10, 3), "Taxi", Decimal("12.50"), "USD")])

    def test_xml_missing_field_names_the_line(self) -> None:
        item = xml_expense("<date>2026-10-03</date>", "<currency>USD</currency>")
        with self.assertRaisesRegex(ReportError, "line 1"):
            read_expenses(write_file(f"<expenses>{item}</expenses>", ".xml"))

    def test_invalid_xml_raises_report_error(self) -> None:
        with self.assertRaises(ReportError):
            read_expenses(write_file("<expenses><expense>", ".xml"))

    def test_extension_is_case_insensitive(self) -> None:
        self.assertEqual(len(read_expenses(write_file(JSON_TWO, ".JSON"))), 2)

    def test_unsupported_extension(self) -> None:
        with self.assertRaisesRegex(ReportError, "unsupported"):
            read_expenses(write_file("x", ".xlsx"))


class Cli(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "report", *args], capture_output=True, text=True)

    def test_prints_the_summary(self) -> None:
        out = self.run_cli("data/sample.csv")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("expenses from", out.stdout)

    def test_cli_reads_json(self) -> None:
        out = self.run_cli(str(write_file(JSON_TWO, ".json")))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("expenses from", out.stdout)

    def test_bad_file_exits_1(self) -> None:
        self.assertEqual(self.run_cli("missing.csv").returncode, 1)


if __name__ == "__main__":
    unittest.main()
