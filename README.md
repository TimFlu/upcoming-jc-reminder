# JC Test Scheduling

This repository exists only to generate a weekly GitHub pull request for the upcoming Journal Club presenter.

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
- writes [reminders/upcoming.md](/Users/tflueh/Documents/Playground/reminders/upcoming.md)
- writes [reminders/last-run.md](/Users/tflueh/Documents/Playground/reminders/last-run.md)
- sets the PR title/body so Teams notifications show the presenter and date

The workflow at [.github/workflows/create-upcoming-reminder-pr.yml](/Users/tflueh/Documents/Playground/.github/workflows/create-upcoming-reminder-pr.yml) runs every Thursday at minutes `:38`, `:43`, `:48`, `:53`, and `:58` of each hour in `UTC`.

## Optional repository variables

- `REMINDER_INPUT_PATH`
- `REMINDER_OUTPUT_PATH`
- `REMINDER_STATUS_OUTPUT_PATH`
- `REMINDER_DATE_COLUMN`
- `REMINDER_NAME_COLUMN`
- `REMINDER_LOOKAHEAD_DAYS`

The current defaults already match the CSV in this repository.
