"""Export applications as CSV or standalone HTML."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from .db import FIELDS, list_applications, status_counts


def export_csv(database: str | Path, destination: str | Path) -> int:
    rows = list_applications(database)
    output = Path(destination).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("id", *FIELDS, "created_at", "updated_at"))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def export_html(database: str | Path, destination: str | Path) -> int:
    rows = list_applications(database)
    counts = status_counts(database)
    cards = "".join(f"<div class='stat'><strong>{count}</strong><span>{escape(status)}</span></div>" for status, count in counts.items())
    table_rows = "".join(
        "<tr>"
        + f"<td>{row['id']}</td><td><strong>{escape(row['company'])}</strong><small>{escape(row['city'])}</small></td>"
        + f"<td>{escape(row['role'])}</td><td><span class='badge'>{escape(row['status'])}</span></td>"
        + f"<td>{escape(row['applied_on'] or '—')}</td>"
        + "</tr>"
        for row in rows
    )
    html = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bewerbungsübersicht · Python-Lernprojekt</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f6f7f2;color:#263736;font:16px/1.5 'Segoe UI',Arial,sans-serif}}
.wrap{{max-width:1050px;margin:auto;padding:48px 24px}}.eyebrow{{color:#327366;text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:.16em}}
h1{{font-size:clamp(32px,5vw,52px);margin:8px 0 10px}}.intro{{color:#64736d;margin-bottom:32px}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:32px}}
.stat{{background:#fff;border:1px solid #e1e8e1;border-radius:15px;padding:18px;display:flex;flex-direction:column}}.stat strong{{font-size:32px;color:#205f60}}.stat span{{color:#60716b}}
.table-wrap{{overflow:auto;background:#fff;border:1px solid #e1e8e1;border-radius:15px}}table{{width:100%;border-collapse:collapse;min-width:680px}}th,td{{padding:17px 20px;text-align:left;border-bottom:1px solid #edf0eb}}
th{{background:#eaf2ec;color:#46645d;font-size:13px}}tr:last-child td{{border-bottom:0}}small{{display:block;color:#87938e;margin-top:3px}}.badge{{display:inline-block;border-radius:30px;padding:5px 11px;background:#e1f1ea;color:#205f60;font-weight:700;font-size:13px}}
.footer{{font-size:13px;color:#77847e;margin-top:20px}}@media(max-width:650px){{.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap"><div class="eyebrow">Python + SQLite · lokales Lernprojekt</div><h1>Bewerbungen im Blick.</h1>
<p class="intro">Eine einfache Übersicht über Entwürfe, versendete Bewerbungen und Antworten.</p>
<div class="stats">{cards}</div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Unternehmen</th><th>Stelle</th><th>Status</th><th>Beworben am</th></tr></thead>
<tbody>{table_rows or '<tr><td colspan="5">Noch keine Einträge vorhanden.</td></tr>'}</tbody></table></div>
<p class="footer">Nur lokal erzeugt. Dieser Bericht wird nicht automatisch hochgeladen oder versendet.</p></div></body></html>"""
    output = Path(destination).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return len(rows)
