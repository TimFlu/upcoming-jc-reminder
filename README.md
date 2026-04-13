# JC Test Scheduling

This repository exists only to open a GitHub issue on Wednesday morning for the Journal Club presenter of the current week and the following week.

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
- finds the presenter for this calendar week and the following calendar week
- writes local reminder files for inspection
- generates an issue title and issue body for GitHub Actions

The workflow at [.github/workflows/create-upcoming-reminder-pr.yml](/Users/tflueh/Documents/Playground/.github/workflows/create-upcoming-reminder-pr.yml) runs every Wednesday at `07:00 UTC`, which is `09:00 CEST` in Zurich during summer time, and creates a fresh issue labeled `jc-reminder`.

## Optional repository variables

- `REMINDER_INPUT_PATH`
- `REMINDER_OUTPUT_PATH`
- `REMINDER_STATUS_OUTPUT_PATH`
- `REMINDER_DATE_COLUMN`
- `REMINDER_NAME_COLUMN`
- `REMINDER_LOOKAHEAD_DAYS`

The current defaults already match the CSV in this repository.
