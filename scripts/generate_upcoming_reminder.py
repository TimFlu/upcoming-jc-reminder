from __future__ import annotations

import argparse
import csv
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET


DEFAULT_INPUT = "data/JC schedule.xlsx"
DEFAULT_OUTPUT = "reminders/upcoming.md"
EXCEL_EPOCH = date(1899, 12, 30)
XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reminder file for upcoming date/name entries."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Path to the source CSV or Excel file.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Path to the generated markdown file.",
    )
    parser.add_argument(
        "--date-column",
        default="Date",
        help="Column containing the target date.",
    )
    parser.add_argument(
        "--name-column",
        default="Presenter",
        help="Column containing the name to mention.",
    )
    parser.add_argument(
        "--lookahead-days",
        type=int,
        default=7,
        help="Include rows whose dates fall within this many days from today.",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override today's date in YYYY-MM-DD format for testing.",
    )
    return parser.parse_args()


def load_table(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    if path.suffix.lower() == ".xlsx":
        return load_xlsx_table(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def load_xlsx_table(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        sheet_path = find_first_sheet_path(archive)
        sheet_root = ET.fromstring(archive.read(sheet_path))

    rows: list[list[str]] = []
    for row in sheet_root.findall(".//main:sheetData/main:row", XML_NS):
        values: list[str] = []
        for cell in row.findall("main:c", XML_NS):
            cell_type = cell.attrib.get("t")
            value_node = cell.find("main:v", XML_NS)
            value = "" if value_node is None or value_node.text is None else value_node.text
            if cell_type == "s" and value:
                value = shared_strings[int(value)]
            values.append(value)
        rows.append(values)

    if not rows:
        return []

    headers = [str(cell).strip() for cell in rows[0]]
    output: list[dict[str, str]] = []
    for row in rows[1:]:
        entry: dict[str, str] = {}
        for index, header in enumerate(headers):
            entry[header] = row[index] if index < len(row) else ""
        output.append(entry)
    return output


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("main:si", XML_NS):
        parts = [node.text or "" for node in item.findall(".//main:t", XML_NS)]
        shared_strings.append("".join(parts))
    return shared_strings


def find_first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in workbook_rels}

    first_sheet = workbook_root.find("main:sheets", XML_NS)[0]
    rel_id = first_sheet.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
    target = rel_map[rel_id]
    if not target.startswith("xl/"):
        target = f"xl/{target.lstrip('/')}"
    return target


def parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    if text.isdigit():
        return EXCEL_EPOCH + timedelta(days=int(text))

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def build_output(upcoming: list[dict[str, str | int | date]], start: date, end: date) -> str:
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


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    rows = load_table(input_path)
    if rows:
        available_columns = set(rows[0].keys())
        required_columns = {args.date_column, args.name_column}
        missing = required_columns.difference(available_columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise KeyError(f"Missing required columns: {missing_text}")

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

        days_remaining = (target_date - today).days
        if today <= target_date <= window_end:
            upcoming.append(
                {
                    "target_date": target_date,
                    "person_name": person_name,
                    "days_remaining": days_remaining,
                }
            )

    upcoming.sort(key=lambda row: (row["target_date"], row["person_name"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_output(upcoming, today, window_end), encoding="utf-8")


if __name__ == "__main__":
    main()
