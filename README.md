# JC Test Scheduling

This repository exists only to open a GitHub issue for the upcoming Journal Club presenter.

## Source file

The schedule is stored in [data/JC test schedule.csv](/Users/tflueh/Documents/Playground/data/JC%20test%20schedule.csv).

Expected columns:

- `Date`
- `Presenter`
- `Paper`

Rows with presenter `--` are ignored.

## What the automation does

The script at [scripts/generate_upcoming_reminder.py](/Users/tflueh/Documents/Playground/scripts/generate_upcoming_reminder.py):

- reads the CSV schedule
- finds presenters in the next 7 days
- writes local reminder files for inspection
- generates an issue title and issue body for GitHub Actions

The workflow at [.github/workflows/create-upcoming-reminder-pr.yml](/Users/tflueh/Documents/Playground/.github/workflows/create-upcoming-reminder-pr.yml) runs every Thursday at minutes `:38`, `:43`, `:48`, `:53`, and `:58` of each hour in `UTC` and creates or updates an issue labeled `jc-reminder`.

## Optional repository variables

- `REMINDER_INPUT_PATH`
- `REMINDER_OUTPUT_PATH`
- `REMINDER_STATUS_OUTPUT_PATH`
- `REMINDER_DATE_COLUMN`
- `REMINDER_NAME_COLUMN`
- `REMINDER_LOOKAHEAD_DAYS`

The current defaults already match the CSV in this repository.
