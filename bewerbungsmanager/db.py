"""SQLite storage and validation for the application tracker."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sqlite3
from typing import Iterator
from urllib.parse import urlparse

STATUSES = ("Entwurf", "Gesendet", "Antwort", "Interview", "Zusage", "Absage")
FIELDS = ("company", "role", "city", "status", "applied_on", "url", "notes")


@contextmanager
def connect(database: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(database).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            city TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Entwurf',
            applied_on TEXT,
            url TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS applications_status_idx ON applications(status)")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _clean(field: str, value: object) -> str | None:
    if field not in FIELDS:
        raise ValueError(f"Unbekanntes Feld: {field}")
    if field == "applied_on":
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError as error:
            raise ValueError("Datum im Format JJJJ-MM-TT eingeben.") from error
    text = str(value or "").strip()
    if field in ("company", "role") and not text:
        raise ValueError(f"{field} darf nicht leer sein.")
    if len(text) > (2000 if field == "notes" else 300):
        raise ValueError(f"{field} ist zu lang.")
    if field == "status" and text not in STATUSES:
        raise ValueError("Unbekannter Status. Erlaubt: " + ", ".join(STATUSES))
    if field == "url" and text:
        parsed = urlparse(text)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Link muss mit http:// oder https:// beginnen.")
    return text


def _validate_sent(status: str, applied_on: str | None) -> None:
    if status != "Entwurf" and applied_on is None:
        raise ValueError("Für einen versendeten oder späteren Status ist das Bewerbungsdatum nötig.")


def add_application(database: str | Path, *, company: str, role: str, city: str = "", status: str = "Entwurf", applied_on: str | None = None, url: str = "", notes: str = "") -> int:
    data = {field: _clean(field, value) for field, value in {
        "company": company, "role": role, "city": city, "status": status,
        "applied_on": applied_on, "url": url, "notes": notes,
    }.items()}
    _validate_sent(data["status"], data["applied_on"])
    with connect(database) as db:
        result = db.execute(
            "INSERT INTO applications (company, role, city, status, applied_on, url, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            tuple(data[field] for field in FIELDS),
        )
        return int(result.lastrowid)


def get_application(database: str | Path, application_id: int) -> dict | None:
    with connect(database) as db:
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(row) if row else None


def list_applications(database: str | Path, *, status: str | None = None, search: str | None = None) -> list[dict]:
    query = "SELECT * FROM applications WHERE 1 = 1"
    params: list[str] = []
    if status:
        query += " AND status = ?"
        params.append(_clean("status", status))
    if search:
        query += " AND (company LIKE ? OR role LIKE ? OR city LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend((term, term, term))
    query += " ORDER BY updated_at DESC, id DESC"
    with connect(database) as db:
        return [dict(row) for row in db.execute(query, params).fetchall()]


def update_application(database: str | Path, application_id: int, **changes: object) -> dict:
    if not changes:
        raise ValueError("Mindestens ein Feld zum Ändern angeben.")
    cleaned = {field: _clean(field, value) for field, value in changes.items()}
    with connect(database) as db:
        old = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if not old:
            raise ValueError(f"Bewerbung #{application_id} nicht gefunden.")
        new_status = cleaned.get("status", old["status"])
        new_date = cleaned.get("applied_on", old["applied_on"])
        _validate_sent(new_status, new_date)
        set_clause = ", ".join(f"{field} = ?" for field in cleaned)
        db.execute(
            f"UPDATE applications SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            (*cleaned.values(), application_id),
        )
        row = db.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        return dict(row)


def delete_application(database: str | Path, application_id: int) -> bool:
    with connect(database) as db:
        result = db.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        return result.rowcount > 0


def status_counts(database: str | Path) -> dict[str, int]:
    with connect(database) as db:
        rows = db.execute("SELECT status, COUNT(*) AS count FROM applications GROUP BY status").fetchall()
    found = {row["status"]: row["count"] for row in rows}
    return {status: found.get(status, 0) for status in STATUSES}
