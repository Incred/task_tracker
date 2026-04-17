# task-tracker

A minimal CLI for logging work time. Entries are stored in a local SQLite database (`~/.task_tracker.db`), so nothing leaves your machine.

## Requirements

Python 3.10+, no third-party dependencies.

## Installation

```bash
git clone https://github.com/Incred/task-tracker.git
cd task-tracker
chmod +x tracker.py

# optional: put it on PATH
ln -s "$PWD/tracker.py" ~/.local/bin/tracker
```

## Commands

### `add` — log a time entry

```
tracker add START END DESC [-d DATE]
```

```bash
tracker add 09:00 10:30 "code review"
tracker add 14:00 17:00 "refactoring auth module" -d 2024-03-15
tracker add 09:00 09:30 "standup" -d yesterday
```

`START` and `END` are `HH:MM` (seconds are accepted but ignored).  
`DATE` is `YYYY-MM-DD`, `today`, or `yesterday`. Defaults to today.

---

### `list` — show all entries

```
tracker list [-d DATE] [--from DATE] [--to DATE]
```

```bash
tracker list                        # everything
tracker list -d today               # just today
tracker list --from 2024-03-01 --to 2024-03-31  # a date range
```

Output includes per-day and grand totals:

```
  ID        Date  Start    End  Duration  Description
------------------------------------------------------------------------------------------------
   5  2024-03-15  09:00  10:30    1h 30m  code review
   6  2024-03-15  14:00  17:00    3h 00m  refactoring auth module
                                  4h 30m  ← day total

total: 4h 30m  (2 entries)
```

---

### `report` — grouped summary

```
tracker report [--from DATE] [--to DATE]
```

```bash
tracker report
tracker report --from 2024-03-01 --to 2024-03-31
```

```
==========================================================
  2024-03-15 → 2024-03-15
==========================================================

  2024-03-15  [4h 30m]
  --------------------------------------
    09:00–10:30    1h 30m  code review
    14:00–17:00    3h 00m  refactoring auth module

==========================================================
  total: 4h 30m  (1 day(s), 2 task(s))
==========================================================
```

---

### `delete` — remove an entry by ID

```
tracker delete ID
```

```bash
tracker delete 5
```

---

### `export` — dump to JSON

```
tracker export [-o FILE] [--from DATE] [--to DATE]
```

```bash
tracker export                              # → export.json
tracker export -o march.json --from 2024-03-01 --to 2024-03-31
```

Output format:

```json
{
  "exported_at": "2024-03-15T18:00:00",
  "total_entries": 2,
  "total_minutes": 270,
  "total_duration": "4h 30m",
  "entries": [
    {
      "id": 5,
      "date": "2024-03-15",
      "start_time": "09:00",
      "end_time": "10:30",
      "description": "code review",
      "duration_minutes": 90,
      "duration": "1h 30m"
    }
  ]
}
```

## Database

Entries are stored in `~/.task_tracker.db` (SQLite). To back it up:

```bash
cp ~/.task_tracker.db ~/backup/task_tracker_$(date +%F).db
```
