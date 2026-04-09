# Personal Finance Dashboard

A small Streamlit app for exploring bank exports from Excel or CSV files.

## Features

- Upload `.csv`, `.xlsx`, or `.xls` files
- Map your bank's date, description, and amount columns
- Summarize income, expenses, and net balance
- View monthly trends and category breakdowns
- Create your own grouping rules based on transaction text
- Manually adjust categories in the transaction table

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
streamlit run app.py
```

## Expected input

The app works best when your export includes:

- a transaction date column
- a text or description column
- either one signed amount column or separate income and expense columns

If your bank uses different names, you can remap them in the sidebar.

## Weekly reminder PR automation

This repository can also automatically open a GitHub pull request each week based on a CSV or Excel file that contains dates and names.

### File format

Store your reminders in `data/events.csv` or point the workflow to another `.csv`, `.xlsx`, or `.xls` file. By default the script expects:

- a `date` column
- a `name` column

Example:

```csv
date,name
2026-04-12,Alice
2026-04-15,Bob
```

### How it works

The script at `scripts/generate_upcoming_reminder.py` reads the file, finds rows whose date falls within the next 7 days, and writes them to `reminders/upcoming.md`.

The GitHub Actions workflow at `.github/workflows/create-upcoming-reminder-pr.yml` runs every Monday at 08:00 UTC and opens or updates a pull request if the generated reminder file changed.

### Workflow configuration

You can customize the workflow with GitHub Actions repository variables:

- `REMINDER_INPUT_PATH`
- `REMINDER_OUTPUT_PATH`
- `REMINDER_DATE_COLUMN`
- `REMINDER_NAME_COLUMN`
- `REMINDER_LOOKAHEAD_DAYS`

If you want to use Excel instead of CSV, upload the workbook to the repository and set `REMINDER_INPUT_PATH` to its path.
