#!/usr/bin/env python3
"""Time tracker — log tasks with start/end times, report and export."""

import argparse
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".task_tracker.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "date TEXT NOT NULL, "
            "start_time TEXT NOT NULL, "
            "end_time TEXT NOT NULL, "
            "description TEXT NOT NULL)"
        )


def parse_time(value: str) -> str:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Bad time '{value}', expected HH:MM")


def parse_date(value: str) -> str:
    s = value.lower()
    if s == "today":
        return date.today().isoformat()
    if s == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise argparse.ArgumentTypeError(f"Bad date '{value}', expected YYYY-MM-DD")


def minutes_between(start: str, end: str) -> int:
    fmt = "%H:%M"
    delta = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
    return int(delta.total_seconds() // 60)


def hm(minutes: int) -> str:
    if minutes < 0:
        return "0h 00m"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def enrich(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["duration_minutes"] = minutes_between(d["start_time"], d["end_time"])
    d["duration"] = hm(d["duration_minutes"])
    return d


def fetch_entries(args) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM entries ORDER BY date, start_time").fetchall()
    return _apply_filters([enrich(r) for r in rows], args)


def cmd_add(args):
    day = args.date or date.today().isoformat()
    start = parse_time(args.start)
    end = parse_time(args.end)
    if minutes_between(start, end) < 0:
        print("end time must be after start time")
        return
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO entries (date, start_time, end_time, description) VALUES (?,?,?,?)",
            (day, start, end, args.description),
        )
    print(f"#{cur.lastrowid}  {day}  {start}–{end}  {args.description!r}")


def _apply_filters(entries, args):
    if getattr(args, "date", None):
        entries = [e for e in entries if e["date"] == args.date]
    if getattr(args, "from_date", None):
        entries = [e for e in entries if e["date"] >= args.from_date]
    if getattr(args, "to_date", None):
        entries = [e for e in entries if e["date"] <= args.to_date]
    return entries


def cmd_list(args):
    entries = fetch_entries(args)

    if not entries:
        print("no entries")
        return

    print(f"{'ID':>4}  {'Date':>10}  {'Start':>5}  {'End':>5}  {'Duration':>8}  Description")
    print("-" * 96)

    cur_date = None
    day_total = grand_total = 0
    for e in entries:
        if e["date"] != cur_date:
            if cur_date is not None:
                print(f"{'':>4}  {'':>10}  {'':>5}  {'':>5}  {hm(day_total):>8}  ← day total")
                day_total = 0
            cur_date = e["date"]
        print(f"{e['id']:>4}  {e['date']:>10}  {e['start_time']:>5}  {e['end_time']:>5}"
              f"  {e['duration']:>8}  {e['description']}")
        day_total += e["duration_minutes"]
        grand_total += e["duration_minutes"]

    print(f"{'':>4}  {'':>10}  {'':>5}  {'':>5}  {hm(day_total):>8}  ← day total")
    print(f"\ntotal: {hm(grand_total)}  ({len(entries)} entries)")


def cmd_delete(args):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id=?", (args.id,)).fetchone()
        if not row:
            print(f"entry #{args.id} not found")
            return
        e = dict(row)
        print(f"deleting #{e['id']}: {e['date']}  {e['start_time']}–{e['end_time']}  {e['description']!r}")
        conn.execute("DELETE FROM entries WHERE id=?", (args.id,))
    print("done")


def cmd_report(args):
    entries = fetch_entries(args)
    if not entries:
        print("nothing to report")
        return

    by_date: dict[str, list] = {}
    for e in entries:
        by_date.setdefault(e["date"], []).append(e)

    grand = sum(e["duration_minutes"] for e in entries)
    sep = "=" * 58

    print(f"\n{sep}")
    print(f"  {entries[0]['date']} → {entries[-1]['date']}")
    print(sep)
    for d, day_entries in sorted(by_date.items()):
        day_total = sum(e["duration_minutes"] for e in day_entries)
        print(f"\n  {d}  [{hm(day_total)}]")
        print(f"  {'-' * 38}")
        for e in day_entries:
            print(f"    {e['start_time']}–{e['end_time']}  {e['duration']:>8}  {e['description']}")
    print(f"\n{sep}")
    print(f"  total: {hm(grand)}  ({len(by_date)} day(s), {len(entries)} task(s))")
    print(f"{sep}\n")


def cmd_export(args):
    entries = fetch_entries(args)
    total_min = sum(e["duration_minutes"] for e in entries)

    out = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "total_entries": len(entries),
        "total_minutes": total_min,
        "total_duration": hm(total_min),
        "entries": entries,
    }

    path = Path(args.output)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"exported {len(entries)} entries → {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracker", description="Simple job time tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add a time entry")
    p.add_argument("start", metavar="START")
    p.add_argument("end", metavar="END")
    p.add_argument("description", metavar="DESC")
    p.add_argument("-d", "--date", metavar="DATE", type=parse_date)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="list entries")
    p.add_argument("-d", "--date", metavar="DATE", type=parse_date)
    p.add_argument("--from", dest="from_date", metavar="DATE", type=parse_date)
    p.add_argument("--to", dest="to_date", metavar="DATE", type=parse_date)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="delete an entry by id")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("report", help="grouped report")
    p.add_argument("--from", dest="from_date", metavar="DATE", type=parse_date)
    p.add_argument("--to", dest="to_date", metavar="DATE", type=parse_date)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("export", help="export to JSON")
    p.add_argument("-o", "--output", metavar="FILE", default="export.json")
    p.add_argument("--from", dest="from_date", metavar="DATE", type=parse_date)
    p.add_argument("--to", dest="to_date", metavar="DATE", type=parse_date)
    p.set_defaults(func=cmd_export)

    return parser


def main():
    init_db()
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
