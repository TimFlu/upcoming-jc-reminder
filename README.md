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

Store your reminders in `data/JC schedule.xlsx` or point the workflow to another `.csv` or `.xlsx` file. For your workbook, the script expects:

- a `Date` column
- a `Presenter` column

Your current workbook already matches that shape: first column = date, second column = presenter.

### How it works

The script at `scripts/generate_upcoming_reminder.py` reads the file, finds rows whose date falls within the next 7 days, skips placeholder presenters such as `--`, and writes them to `reminders/upcoming.md`.

The GitHub Actions workflow at `.github/workflows/create-upcoming-reminder-pr.yml` runs every Monday at 08:00 UTC and opens or updates a pull request if the generated reminder file changed.

### Workflow configuration

You can customize the workflow with GitHub Actions repository variables:

- `REMINDER_INPUT_PATH`
- `REMINDER_OUTPUT_PATH`
- `REMINDER_DATE_COLUMN`
- `REMINDER_NAME_COLUMN`
- `REMINDER_LOOKAHEAD_DAYS`

The current defaults already match `data/JC schedule.xlsx`, `Date`, and `Presenter`.
