import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bewerbungsmanager.cli import main
from bewerbungsmanager.db import add_application, delete_application, get_application, list_applications, status_counts, update_application
from bewerbungsmanager.report import export_csv, export_html


class ApplicationTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_crud_search_and_counts(self):
        first = add_application(self.db, company="Nord IT", role="Ausbildung Python", city="Husum")
        second = add_application(self.db, company="Muster AG", role="Entwicklung", city="Kiel", status="Gesendet", applied_on="2026-09-22")
        self.assertEqual(len(list_applications(self.db)), 2)
        self.assertEqual([row["id"] for row in list_applications(self.db, search="husum")], [first])
        self.assertEqual([row["id"] for row in list_applications(self.db, status="Gesendet")], [second])
        changed = update_application(self.db, first, status="Gesendet", applied_on="2026-09-22", notes="Bestätigung eingetroffen")
        self.assertEqual(changed["notes"], "Bestätigung eingetroffen")
        self.assertEqual(status_counts(self.db)["Gesendet"], 2)
        self.assertTrue(delete_application(self.db, second))
        self.assertFalse(delete_application(self.db, second))
        self.assertIsNone(get_application(self.db, second))

    def test_validation_prevents_incorrect_dates_and_links(self):
        with self.assertRaises(ValueError):
            add_application(self.db, company="", role="Entwicklung")
        with self.assertRaises(ValueError):
            add_application(self.db, company="Test", role="Entwicklung", status="Gesendet")
        with self.assertRaises(ValueError):
            add_application(self.db, company="Test", role="Entwicklung", applied_on="22.09.2026")
        with self.assertRaises(ValueError):
            add_application(self.db, company="Test", role="Entwicklung", url="javascript:alert(1)")
        draft = add_application(self.db, company="Test", role="Entwicklung")
        with self.assertRaises(ValueError):
            update_application(self.db, draft, status="Interview")
        self.assertEqual(get_application(self.db, draft)["status"], "Entwurf")

    def test_csv_and_html_export(self):
        add_application(self.db, company="<Demo & Co>", role="Ausbildung", city="Kiel", notes="fiktiv")
        csv_file = Path(self.temp.name) / "ausgabe.csv"
        html_file = Path(self.temp.name) / "bericht.html"
        self.assertEqual(export_csv(self.db, csv_file), 1)
        self.assertEqual(export_html(self.db, html_file), 1)
        with csv_file.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(rows[0]["company"], "<Demo & Co>")
        html = html_file.read_text(encoding="utf-8")
        self.assertIn("&lt;Demo &amp; Co&gt;", html)
        self.assertNotIn("<Demo & Co>", html)

    def test_cli_demo_and_delete_confirmation(self):
        arguments = ["--db", str(self.db)]
        self.assertEqual(main(arguments + ["demo"]), 0)
        self.assertEqual(len(list_applications(self.db)), 3)
        self.assertEqual(main(arguments + ["demo"]), 2)
        first = list_applications(self.db)[0]["id"]
        self.assertEqual(main(arguments + ["delete", str(first)]), 2)
        self.assertIsNotNone(get_application(self.db, first))
        self.assertEqual(main(arguments + ["delete", str(first), "--yes"]), 0)


if __name__ == "__main__":
    unittest.main()
