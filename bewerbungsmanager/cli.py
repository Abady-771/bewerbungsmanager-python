"""German command-line interface for the application tracker."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from .db import STATUSES, add_application, connect, delete_application, get_application, list_applications, status_counts, update_application
from .report import export_csv, export_html


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="bewerbungsmanager",
        description="Bewerbungen lokal mit Python und SQLite verwalten.",
    )
    root.add_argument("--db", default="bewerbungen.sqlite3", help="Pfad zur lokalen SQLite-Datei")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Leere Datenbank anlegen")

    add = commands.add_parser("add", help="Bewerbung anlegen")
    add.add_argument("--company", required=True, help="Unternehmen")
    add.add_argument("--role", required=True, help="Stelle")
    add.add_argument("--city", default="", help="Ort")
    add.add_argument("--status", choices=STATUSES, default="Entwurf")
    add.add_argument("--applied-on", help="Bewerbungsdatum JJJJ-MM-TT")
    add.add_argument("--url", default="", help="Link zur Stelle")
    add.add_argument("--notes", default="", help="Notizen")

    listing = commands.add_parser("list", help="Bewerbungen anzeigen")
    listing.add_argument("--status", choices=STATUSES)
    listing.add_argument("--search", help="Firma, Stelle oder Ort durchsuchen")

    show = commands.add_parser("show", help="Details einer Bewerbung")
    show.add_argument("id", type=int)

    update = commands.add_parser("update", help="Bewerbung ändern")
    update.add_argument("id", type=int)
    for field in ("company", "role", "city", "applied_on", "url", "notes"):
        update.add_argument("--" + field.replace("_", "-"))
    update.add_argument("--status", choices=STATUSES)

    delete = commands.add_parser("delete", help="Eintrag löschen")
    delete.add_argument("id", type=int)
    delete.add_argument("--yes", action="store_true", help="Löschen bestätigen")

    commands.add_parser("stats", help="Anzahl je Status anzeigen")
    export = commands.add_parser("export", help="CSV oder HTML erstellen")
    export.add_argument("--file", required=True, help="Zieldatei mit .csv oder .html")
    commands.add_parser("demo", help="Fiktive Beispiele in eine leere Datenbank einfügen")
    return root


def _print_row(row: dict) -> None:
    location = f" · {row['city']}" if row["city"] else ""
    applied = f" · {row['applied_on']}" if row["applied_on"] else ""
    print(f"#{row['id']}  {row['company']} — {row['role']}{location}  [{row['status']}]{applied}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    database = Path(args.db)
    try:
        if args.command == "init":
            with connect(database):
                pass
            print(f"Datenbank bereit: {database}")
        elif args.command == "add":
            application_id = add_application(database, company=args.company, role=args.role, city=args.city, status=args.status, applied_on=args.applied_on, url=args.url, notes=args.notes)
            print(f"Bewerbung #{application_id} angelegt.")
        elif args.command == "list":
            rows = list_applications(database, status=args.status, search=args.search)
            if not rows:
                print("Keine Bewerbungen gefunden.")
            for row in rows:
                _print_row(row)
            print(f"{len(rows)} Einträge")
        elif args.command == "show":
            row = get_application(database, args.id)
            if not row:
                raise ValueError(f"Bewerbung #{args.id} nicht gefunden.")
            for field, value in row.items():
                print(f"{field}: {value or '—'}")
        elif args.command == "update":
            changes = {field: getattr(args, field) for field in ("company", "role", "city", "status", "applied_on", "url", "notes") if getattr(args, field) is not None}
            row = update_application(database, args.id, **changes)
            print("Aktualisiert:")
            _print_row(row)
        elif args.command == "delete":
            if not args.yes:
                print("Zum Löschen --yes hinzufügen.", file=sys.stderr)
                return 2
            if not delete_application(database, args.id):
                raise ValueError(f"Bewerbung #{args.id} nicht gefunden.")
            print(f"Bewerbung #{args.id} gelöscht.")
        elif args.command == "stats":
            counts = status_counts(database)
            for status, count in counts.items():
                print(f"{status:12} {count}")
            print(f"Gesamt       {sum(counts.values())}")
        elif args.command == "export":
            output = Path(args.file)
            if output.suffix.lower() == ".csv":
                count = export_csv(database, output)
            elif output.suffix.lower() in (".html", ".htm"):
                count = export_html(database, output)
            else:
                raise ValueError("Dateiendung .csv oder .html verwenden.")
            print(f"{count} Einträge exportiert: {output}")
        elif args.command == "demo":
            if list_applications(database):
                raise ValueError("Demo-Daten nur in eine leere Datenbank einfügen.")
            add_application(database, company="Beispiel Digital GmbH", role="Ausbildung Anwendungsentwicklung", city="Kiel", status="Entwurf", notes="Nur fiktive Testdaten")
            add_application(database, company="Muster Software AG", role="Praktikum Softwareentwicklung", city="Hamburg", status="Gesendet", applied_on="2026-09-01", notes="Nur fiktive Testdaten")
            add_application(database, company="Demo Technik KG", role="Ausbildung Fachinformatik", city="Flensburg", status="Interview", applied_on="2026-08-20", notes="Nur fiktive Testdaten")
            print("3 fiktive Beispiele angelegt.")
        return 0
    except (ValueError, OSError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
