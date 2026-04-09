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
        description="Generate reminder files and issue text for upcoming JC presenters."
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
    lines.append("Please review the upcoming presenters and dates.")
    lines.append("")
    return "\n".join(lines)


def build_status_output(
    future_presenters: list[dict[str, str | int | date]],
    start: date,
    end: date,
) -> str:
    lines = [
        "# Reminder workflow status",
        "",
        f"Window: {start} through {end}",
        "",
    ]

    if future_presenters:
        first = future_presenters[0]
        lines.append(f"Next presenter: {first['person_name']}")
        lines.append(f"Next date: {first['target_date']}")
        paper = str(first.get("paper_title", "")).strip()
        if paper:
            lines.append(f"Paper/topic: {paper}")
        if len(future_presenters) > 1:
            second = future_presenters[1]
            lines.append(f"Following presenter: {second['person_name']}")
            lines.append(f"Following date: {second['target_date']}")
            second_paper = str(second.get("paper_title", "")).strip()
            if second_paper:
                lines.append(f"Following paper/topic: {second_paper}")
    else:
        lines.append("Next presenter: none in this window")

    lines.append("")
    return "\n".join(lines)


def build_issue_metadata(
    future_presenters: list[dict[str, str | int | date]],
    start: date,
    end: date,
) -> tuple[str, str]:
    if future_presenters:
        first = future_presenters[0]
        presenter = str(first["person_name"])
        target_date = str(first["target_date"])
        paper = str(first.get("paper_title", "")).strip()
        title = f"JC reminder: {presenter} on {target_date}"

        body_lines = [
            "Please specify the name of your paper / work if it is still missing.",
            "",
            f"Next presenter: **{presenter}**",
            f"Next date: **{target_date}**",
        ]
        if paper:
            body_lines.append(f"Next paper / work: **{paper}**")
        else:
            body_lines.append("Next paper / work: **Please add paper title**")

        if len(future_presenters) > 1:
            second = future_presenters[1]
            second_presenter = str(second["person_name"])
            second_date = str(second["target_date"])
            second_paper = str(second.get("paper_title", "")).strip()
            body_lines.extend(
                [
                    "",
                    f"Following presenter: **{second_presenter}**",
                    f"Following date: **{second_date}**",
                ]
            )
            if second_paper:
                body_lines.append(f"Following paper / work: **{second_paper}**")
            else:
                body_lines.append("Following paper / work: **Please add paper title**")
        body_lines.extend(
            [
                "",
                f"Reminder window: {start} through {end}",
                "",
                "Upcoming presenters from the schedule:",
            ]
        )
        for row in future_presenters[:5]:
            line = f"- {row['target_date']}: {row['person_name']}"
            paper_title = str(row.get("paper_title", "")).strip()
            if paper_title:
                line += f" — {paper_title}"
            body_lines.append(line)

        return title, "\n".join(body_lines)

    title = f"No upcoming JC presenter for {start} to {end}"
    body = (
        f"No presenter is scheduled in the reminder window from {start} through {end}."
    )
    return title, body


def write_github_output(path: Path, issue_title: str, issue_body: str) -> None:
    eof = "CODEX_EOF"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"issue_title<<{eof}\n{issue_title}\n{eof}\n")
        handle.write(f"issue_body<<{eof}\n{issue_body}\n{eof}\n")


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
    future_presenters: list[dict[str, str | int | date]] = []
    for row in rows:
        target_date = parse_date(row.get(args.date_column, ""))
        person_name = str(row.get(args.name_column, "")).strip()
        if target_date is None or not person_name or person_name == "--":
            continue
        presenter_data = {
            "target_date": target_date,
            "person_name": person_name,
            "days_remaining": (target_date - today).days,
            "paper_title": str(row.get("Paper", "")).strip(),
        }
        if target_date >= today:
            future_presenters.append(presenter_data)
        if today <= target_date <= window_end:
            upcoming.append(presenter_data)

    upcoming.sort(key=lambda row: (row["target_date"], row["person_name"]))
    future_presenters.sort(key=lambda row: (row["target_date"], row["person_name"]))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_upcoming_output(upcoming, today, window_end),
        encoding="utf-8",
    )

    status_output_path = Path(args.status_output)
    status_output_path.parent.mkdir(parents=True, exist_ok=True)
    status_output_path.write_text(
        build_status_output(future_presenters, today, window_end),
        encoding="utf-8",
    )

    if args.github_output:
        issue_title, issue_body = build_issue_metadata(future_presenters, today, window_end)
        write_github_output(Path(args.github_output), issue_title, issue_body)


if __name__ == "__main__":
    main()
