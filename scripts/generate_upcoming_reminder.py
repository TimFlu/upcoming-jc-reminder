from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_INPUT = "data/JC test schedule.csv"
DEFAULT_OUTPUT = "reminders/upcoming.md"
DEFAULT_STATUS_OUTPUT = "reminders/last-run.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate reminder files for upcoming JC presenters."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--status-output", default=DEFAULT_STATUS_OUTPUT)
    parser.add_argument("--date-column", default="Date")
    parser.add_argument("--name-column", default="Presenter")
    parser.add_argument("--lookahead-days", type=int, default=7)
    parser.add_argument("--today", default=None)
    parser.add_argument("--github-output", default=None)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def build_upcoming_output(
    upcoming: list[dict[str, str | int | date]],
    start: date,
    end: date,
) -> str:
    lines = [
        "# Upcoming reminders",
        "",
        f"Generated for {start} through {end}.",
        "",
    ]

    if not upcoming:
        lines.append("No upcoming dates in this window.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Date | Presenter | Days remaining |")
    lines.append("| --- | --- | ---: |")
    for row in upcoming:
        lines.append(
            f"| {row['target_date']} | {row['person_name']} | {row['days_remaining']} |"
        )

    lines.append("")
    lines.append("Please review the upcoming presenters and dates before merging.")
    lines.append("")
    return "\n".join(lines)


def build_status_output(
    upcoming: list[dict[str, str | int | date]],
    start: date,
    end: date,
    generated_at: datetime,
) -> str:
    lines = [
        "# Reminder workflow status",
        "",
        f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Window: {start} through {end}",
        "",
    ]

    if upcoming:
        first = upcoming[0]
        lines.append(f"Next presenter: {first['person_name']}")
        lines.append(f"Next date: {first['target_date']}")
        paper = str(first.get("paper_title", "")).strip()
        if paper:
            lines.append(f"Paper/topic: {paper}")
    else:
        lines.append("Next presenter: none in this window")

    lines.append("")
    return "\n".join(lines)


def build_pr_metadata(
    upcoming: list[dict[str, str | int | date]],
    start: date,
    end: date,
) -> tuple[str, str, str]:
    if upcoming:
        first = upcoming[0]
        presenter = str(first["person_name"])
        target_date = str(first["target_date"])
        title = f"Upcoming JC: {presenter} on {target_date}"
        commit_message = f"Update reminder for {presenter} on {target_date}"

        body_lines = [
            f"Upcoming JC presenter: **{presenter}**",
            "",
            f"Scheduled date: **{target_date}**",
        ]
        paper = str(first.get("paper_title", "")).strip()
        if paper:
            body_lines.extend(["", f"Paper/topic: {paper}"])
        body_lines.extend(
            [
                "",
                f"This automated PR covers reminders from {start} through {end}.",
                "",
                "See `reminders/upcoming.md` for the full window.",
            ]
        )
        return title, "\n".join(body_lines), commit_message

    title = f"No upcoming JC presenter for {start} to {end}"
    body = (
        f"No presenter is scheduled in the reminder window from {start} through {end}.\n\n"
        "This automated PR updates the tracked reminder files for visibility."
    )
    commit_message = f"Update reminder window for {start} to {end}"
    return title, body, commit_message


def write_github_output(path: Path, title: str, body: str, commit_message: str) -> None:
    eof = "CODEX_EOF"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"pr_title={title}\n")
        handle.write(f"commit_message={commit_message}\n")
        handle.write(f"pr_body<<{eof}\n{body}\n{eof}\n")


def main() -> None:
    args = parse_args()
    rows = load_rows(Path(args.input))

    if rows:
        missing = {args.date_column, args.name_column}.difference(rows[0].keys())
        if missing:
            raise KeyError(f"Missing required columns: {', '.join(sorted(missing))}")

    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date()
        if args.today
        else date.today()
    )
    window_end = today + timedelta(days=args.lookahead_days)

    upcoming: list[dict[str, str | int | date]] = []
    for row in rows:
        target_date = parse_date(row.get(args.date_column, ""))
        person_name = str(row.get(args.name_column, "")).strip()
        if target_date is None or not person_name or person_name == "--":
            continue
        if today <= target_date <= window_end:
            upcoming.append(
                {
                    "target_date": target_date,
                    "person_name": person_name,
                    "days_remaining": (target_date - today).days,
                    "paper_title": str(row.get("Paper", "")).strip(),
                }
            )

    upcoming.sort(key=lambda row: (row["target_date"], row["person_name"]))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_upcoming_output(upcoming, today, window_end),
        encoding="utf-8",
    )

    status_output_path = Path(args.status_output)
    status_output_path.parent.mkdir(parents=True, exist_ok=True)
    status_output_path.write_text(
        build_status_output(upcoming, today, window_end, datetime.utcnow()),
        encoding="utf-8",
    )

    if args.github_output:
        title, body, commit_message = build_pr_metadata(upcoming, today, window_end)
        write_github_output(Path(args.github_output), title, body, commit_message)


if __name__ == "__main__":
    main()
