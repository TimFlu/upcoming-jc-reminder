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
        description="Generate reminder files and issue text for weekly JC presenters."
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
        rows = list(csv.DictReader(handle))

    for row in rows:
        extras = row.get(None) or []
        if extras:
            paper = str(row.get("Paper", "")).strip()
            extra_text = ", ".join(part.strip() for part in extras if str(part).strip())
            row["Paper"] = ", ".join(part for part in [paper, extra_text] if part)
            row.pop(None, None)

    return rows


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


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def presenter_line(prefix: str, presenter: dict[str, str | date] | None) -> list[str]:
    if not presenter:
        return [f"{prefix}: **No presenter scheduled**"]

    lines = [
        f"{prefix}: **{presenter['person_name']}**",
        f"{prefix} date: **{presenter['target_date']}**",
    ]
    paper = str(presenter.get("paper_title", "")).strip()
    if paper:
        lines.append(f"{prefix} paper / work: **{paper}**")
    else:
        lines.append(
            f"{prefix} paper / work: **Missing. Please specify the paper / work title.**"
        )
    return lines


def build_upcoming_output(
    this_week_presenter: dict[str, str | date] | None,
    next_week_presenter: dict[str, str | date] | None,
    current_week_start: date,
    next_week_start: date,
) -> str:
    lines = [
        "# Weekly JC reminder",
        "",
        f"This week: {current_week_start} through {current_week_start + timedelta(days=6)}",
    ]
    lines.extend(presenter_line("This week presenter", this_week_presenter))
    lines.extend(
        [
            "",
            f"Following week: {next_week_start} through {next_week_start + timedelta(days=6)}",
        ]
    )
    lines.extend(presenter_line("Following week presenter", next_week_presenter))
    lines.append("")
    return "\n".join(lines)


def build_status_output(
    this_week_presenter: dict[str, str | date] | None,
    next_week_presenter: dict[str, str | date] | None,
    current_week_start: date,
    next_week_start: date,
) -> str:
    lines = [
        "# Reminder workflow status",
        "",
        f"This week starts: {current_week_start}",
        f"Following week starts: {next_week_start}",
        "",
    ]
    lines.extend(presenter_line("This week presenter", this_week_presenter))
    lines.append("")
    lines.extend(presenter_line("Following week presenter", next_week_presenter))
    lines.append("")
    return "\n".join(lines)


def build_issue_metadata(
    this_week_presenter: dict[str, str | date] | None,
    next_week_presenter: dict[str, str | date] | None,
    current_week_start: date,
    next_week_start: date,
) -> tuple[str, str]:
    if this_week_presenter:
        title = (
            f"JC reminder: {this_week_presenter['person_name']} presents this week "
            f"on {this_week_presenter['target_date']}"
        )
    else:
        title = (
            f"JC reminder: no presenter scheduled this week "
            f"({current_week_start} to {current_week_start + timedelta(days=6)})"
        )

    body_lines = []

    if this_week_presenter:
        body_lines.append(
            f"This week, **{this_week_presenter['person_name']}** will present on "
            f"**{this_week_presenter['target_date']}**."
        )
        paper = str(this_week_presenter.get("paper_title", "")).strip()
        if paper:
            body_lines.append(f"The paper / work is **{paper}**.")
        else:
            body_lines.append(
                "The paper / work is **missing** and should be specified."
            )
    else:
        body_lines.append("No presenter is scheduled for this week.")

    body_lines.append("")

    if next_week_presenter:
        body_lines.append(
            f"Following week, it is **{next_week_presenter['person_name']}**'s turn on "
            f"**{next_week_presenter['target_date']}**."
        )
        next_paper = str(next_week_presenter.get("paper_title", "")).strip()
        if next_paper:
            body_lines.append(f"The paper / work is **{next_paper}**.")
        else:
            body_lines.append(
                "The paper / work is **missing** and should be specified."
            )
    else:
        body_lines.append("No presenter is scheduled for the following week.")

    body_lines.extend(
        [
            "",
            f"This week window: {current_week_start} to {current_week_start + timedelta(days=6)}",
            f"Following week window: {next_week_start} to {next_week_start + timedelta(days=6)}",
        ]
    )

    return title, "\n".join(body_lines)


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
    current_week_start = week_start(today)
    next_week_start = current_week_start + timedelta(days=7)
    current_week_end = current_week_start + timedelta(days=6)
    next_week_end = next_week_start + timedelta(days=6)

    presenters: list[dict[str, str | date]] = []
    for row in rows:
        target_date = parse_date(row.get(args.date_column, ""))
        person_name = str(row.get(args.name_column, "")).strip()
        if target_date is None or not person_name or person_name == "--":
            continue
        presenters.append(
            {
                "target_date": target_date,
                "person_name": person_name,
                "paper_title": str(row.get("Paper", "")).strip(),
            }
        )

    presenters.sort(key=lambda row: (row["target_date"], row["person_name"]))

    this_week_presenter = next(
        (
            row
            for row in presenters
            if current_week_start <= row["target_date"] <= current_week_end
        ),
        None,
    )
    next_week_presenter = next(
        (
            row
            for row in presenters
            if next_week_start <= row["target_date"] <= next_week_end
        ),
        None,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_upcoming_output(
            this_week_presenter,
            next_week_presenter,
            current_week_start,
            next_week_start,
        ),
        encoding="utf-8",
    )

    status_output_path = Path(args.status_output)
    status_output_path.parent.mkdir(parents=True, exist_ok=True)
    status_output_path.write_text(
        build_status_output(
            this_week_presenter,
            next_week_presenter,
            current_week_start,
            next_week_start,
        ),
        encoding="utf-8",
    )

    if args.github_output:
        issue_title, issue_body = build_issue_metadata(
            this_week_presenter,
            next_week_presenter,
            current_week_start,
            next_week_start,
        )
        write_github_output(Path(args.github_output), issue_title, issue_body)


if __name__ == "__main__":
    main()
