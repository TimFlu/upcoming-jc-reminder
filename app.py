from __future__ import annotations

import csv
import io
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")


DEFAULT_CATEGORY = "Uncategorized"

DATE_CANDIDATES = [
    "date",
    "booking date",
    "transaction date",
    "value date",
    "buchungsdatum",
    "valutadatum",
    "abschlussdatum",
    "buchungstag",
    "datum",
]

AMOUNT_CANDIDATES = [
    "amount",
    "betrag",
    "value",
    "transaction amount",
    "credit/debit",
    "einzelbetrag",
]

DESCRIPTION_CANDIDATES = [
    "description",
    "details",
    "memo",
    "purpose",
    "merchant",
    "beschreibung",
    "beschreibung1",
    "beschreibung2",
    "beschreibung3",
    "verwendungszweck",
    "text",
]

INCOME_CANDIDATES = ["income", "credit", "gutschrift", "deposit"]
EXPENSE_CANDIDATES = ["expense", "debit", "lastschrift", "withdrawal", "belastung"]


@dataclass
class ColumnSelection:
    date_col: str
    description_col: str
    amount_mode: str
    amount_col: str | None = None
    income_col: str | None = None
    expense_col: str | None = None


def normalize_column_name(name: str) -> str:
    return str(name).strip().lower()


def detect_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {normalize_column_name(col): col for col in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for col in columns:
        normalized_col = normalize_column_name(col)
        if any(candidate in normalized_col for candidate in candidates):
            return col
    return None


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = uploaded_file.name.lower().split(".")[-1]
    if suffix == "csv":
        raw = uploaded_file.getvalue()
        parsing_errors: list[str] = []
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text_sample = raw.decode(encoding)
            except UnicodeDecodeError:
                continue

            try:
                dialect = csv.Sniffer().sniff(text_sample[:4096], delimiters=",;\t|")
                separators = [dialect.delimiter, ";", ",", "\t", "|"]
            except csv.Error:
                separators = [";", ",", "\t", "|"]

            header_skiprows = detect_header_skiprows(text_sample)

            tried: set[str] = set()
            for separator in separators:
                if separator in tried:
                    continue
                tried.add(separator)
                df = try_parse_csv(raw, encoding, separator, parsing_errors, header_skiprows)
                if df is not None:
                    return df

            df = try_parse_csv(raw, encoding, None, parsing_errors, header_skiprows)
            if df is not None:
                return df

        raise ValueError(
            "CSV parsing failed. Please check the delimiter/quoting used in the export. "
            f"Tried multiple common formats. Last errors: {' | '.join(parsing_errors[-3:])}"
        )
    return pd.read_excel(uploaded_file)


def detect_header_skiprows(text: str) -> int | None:
    lines = text.splitlines()
    for index, line in enumerate(lines[:25]):
        normalized = normalize_column_name(line)
        if (
            normalized.count(";") >= 5
            and any(candidate in normalized for candidate in DATE_CANDIDATES)
            and any(candidate in normalized for candidate in DESCRIPTION_CANDIDATES)
        ):
            return index
    return None


def try_parse_csv(
    raw: bytes,
    encoding: str,
    separator: str | None,
    parsing_errors: list[str],
    header_skiprows: int | None,
) -> pd.DataFrame | None:
    separator_label = "auto" if separator is None else repr(separator)
    base_options = {
        "encoding": encoding,
        "engine": "python",
        "on_bad_lines": "skip",
    }
    if separator is None:
        base_options["sep"] = None
    else:
        base_options["sep"] = separator

    skiprow_candidates = [header_skiprows] if header_skiprows is not None else []
    skiprow_candidates.extend(range(0, 12))

    tried_skiprows: set[int] = set()
    for skiprows in skiprow_candidates:
        if skiprows in tried_skiprows:
            continue
        tried_skiprows.add(skiprows)
        try:
            df = pd.read_csv(io.BytesIO(raw), skiprows=skiprows, **base_options)
        except (pd.errors.ParserError, UnicodeDecodeError, csv.Error) as exc:
            parsing_errors.append(f"{encoding}/{separator_label}/skip={skiprows}: {exc}")
            continue

        normalized_columns = [normalize_column_name(col) for col in df.columns]
        non_empty_rows = len(df.dropna(how="all"))
        looks_like_table = (
            df.shape[1] >= 3
            and non_empty_rows >= 2
            and len(set(normalized_columns)) > 1
        )
        has_useful_header = any(
            candidate in " ".join(normalized_columns)
            for candidate in DATE_CANDIDATES + AMOUNT_CANDIDATES + DESCRIPTION_CANDIDATES
        )

        if looks_like_table and has_useful_header:
            return df
        if looks_like_table and skiprows > 0:
            return df

    return None


def build_column_selection(df: pd.DataFrame) -> ColumnSelection:
    columns = list(df.columns)
    date_default = detect_column(columns, DATE_CANDIDATES) or columns[0]
    description_default = detect_column(columns, DESCRIPTION_CANDIDATES) or columns[0]
    amount_default = detect_column(columns, AMOUNT_CANDIDATES)
    income_default = detect_column(columns, INCOME_CANDIDATES)
    expense_default = detect_column(columns, EXPENSE_CANDIDATES)

    has_split_amounts = income_default is not None and expense_default is not None
    amount_mode_default = "Separate income/expense columns" if has_split_amounts else "Single signed amount column"

    st.sidebar.header("Column Mapping")
    date_col = st.sidebar.selectbox("Date column", columns, index=columns.index(date_default))
    description_col = st.sidebar.selectbox(
        "Description column",
        columns,
        index=columns.index(description_default),
    )
    amount_mode = st.sidebar.radio(
        "Amount format",
        ["Single signed amount column", "Separate income/expense columns"],
        index=0 if amount_mode_default == "Single signed amount column" else 1,
    )

    if amount_mode == "Single signed amount column":
        default_index = columns.index(amount_default) if amount_default in columns else 0
        amount_col = st.sidebar.selectbox("Amount column", columns, index=default_index)
        return ColumnSelection(
            date_col=date_col,
            description_col=description_col,
            amount_mode=amount_mode,
            amount_col=amount_col,
        )

    income_index = columns.index(income_default) if income_default in columns else 0
    expense_index = columns.index(expense_default) if expense_default in columns else 0
    income_col = st.sidebar.selectbox("Income column", columns, index=income_index)
    expense_col = st.sidebar.selectbox("Expense column", columns, index=expense_index)
    return ColumnSelection(
        date_col=date_col,
        description_col=description_col,
        amount_mode=amount_mode,
        income_col=income_col,
        expense_col=expense_col,
    )


def coerce_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace("'", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def extract_counterparty(description: str) -> str:
    text = str(description or "").strip()
    if not text:
        return ""
    first_part = text.split("|")[0].strip()
    return first_part.split(";")[0].strip()


def prepare_transactions(df: pd.DataFrame, selection: ColumnSelection) -> pd.DataFrame:
    result = df.copy()
    result["date"] = pd.to_datetime(result[selection.date_col], errors="coerce", dayfirst=True)
    description_columns = [
        col
        for col in result.columns
        if normalize_column_name(col).startswith("beschreibung")
    ]
    if description_columns:
        result["description"] = (
            result[description_columns]
            .fillna("")
            .astype(str)
            .apply(
                lambda row: " | ".join(part.strip() for part in row if part and part.strip()),
                axis=1,
            )
        )
    else:
        result["description"] = result[selection.description_col].fillna("").astype(str)

    if selection.amount_mode == "Single signed amount column":
        result["amount"] = coerce_numeric(result[selection.amount_col])
    else:
        income = coerce_numeric(result[selection.income_col])
        expense = coerce_numeric(result[selection.expense_col]).abs()
        result["amount"] = income - expense

    result = result.dropna(subset=["date"]).copy()
    result["month"] = result["date"].dt.to_period("M").astype(str)
    result["type"] = result["amount"].apply(lambda value: "Income" if value >= 0 else "Expense")
    result["abs_amount"] = result["amount"].abs()
    result["is_twint"] = result["description"].str.contains("twint", case=False, na=False)
    result["payment_channel"] = result["is_twint"].map({True: "TWINT", False: "Other"})
    result["counterparty"] = result["description"].apply(extract_counterparty)
    result["twint_receiver"] = result.apply(
        lambda row: row["counterparty"] if row["is_twint"] else "",
        axis=1,
    )
    result["transaction_id"] = (
        result["date"].dt.strftime("%Y-%m-%d")
        + "|"
        + result["description"].astype(str)
        + "|"
        + result["amount"].round(2).astype(str)
    )
    return result


def initialize_rules():
    if "rules" not in st.session_state:
        st.session_state.rules = pd.DataFrame(
            [
                {"keyword": "salary", "category": "Salary"},
                {"keyword": "rent", "category": "Rent"},
                {"keyword": "anteil mietzins", "category": "Rent"},
                {"keyword": "twint", "category": "TWINT"},
                {"keyword": "groceries", "category": "Groceries"},
                {"keyword": "supermarket", "category": "Groceries"},
                {"keyword": "restaurant", "category": "Groceries"},
            ]
        )
    if "manual_categories" not in st.session_state:
        st.session_state.manual_categories = {}


def apply_rules(transactions: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    categorized = transactions.copy()
    categorized["category"] = DEFAULT_CATEGORY
    descriptions = categorized["description"].str.lower()
    counterparties = categorized["counterparty"].fillna("").str.lower()

    for _, rule in rules.dropna(subset=["keyword", "category"]).iterrows():
        keyword = str(rule["keyword"]).strip().lower()
        category = str(rule["category"]).strip()
        if not keyword or not category:
            continue
        mask = (
            descriptions.str.contains(keyword, na=False)
            | counterparties.str.contains(keyword, na=False)
        )
        categorized.loc[mask, "category"] = category

    if st.session_state.manual_categories:
        override_map = categorized["transaction_id"].map(st.session_state.manual_categories)
        categorized["category"] = override_map.fillna(categorized["category"])

    return categorized


def show_summary(transactions: pd.DataFrame):
    income = transactions.loc[transactions["amount"] > 0, "amount"].sum()
    expenses = transactions.loc[transactions["amount"] < 0, "amount"].sum()
    net = transactions["amount"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total income", f"{income:,.2f}")
    col2.metric("Total expenses", f"{abs(expenses):,.2f}")
    col3.metric("Net", f"{net:,.2f}")


def show_charts(transactions: pd.DataFrame, group_column: str, selected_month: str):
    daily = (
        transactions.assign(day=transactions["date"].dt.date)
        .groupby(["day", "type"], as_index=False)["abs_amount"]
        .sum()
        .sort_values("day")
    )
    category_totals = (
        transactions.groupby(group_column, as_index=False)["abs_amount"]
        .sum()
        .sort_values("abs_amount", ascending=False)
    )
    expenses = transactions[transactions["amount"] < 0].copy()
    expense_by_category = (
        expenses.groupby(group_column, as_index=False)["abs_amount"]
        .sum()
        .sort_values("abs_amount", ascending=False)
    )

    left, right = st.columns(2)
    with left:
        st.subheader(f"Daily trend for {selected_month}")
        st.plotly_chart(
            px.bar(
                daily,
                x="day",
                y="abs_amount",
                color="type",
                barmode="group",
                labels={"day": "Date", "abs_amount": "Amount"},
            ),
            use_container_width=True,
        )

    with right:
        st.subheader(f"Expenses by {group_column.replace('_', ' ')}")
        if expense_by_category.empty:
            st.info("No expense rows found for the current filters.")
        else:
            st.plotly_chart(
                px.pie(
                    expense_by_category,
                    names=group_column,
                    values="abs_amount",
                ),
                use_container_width=True,
            )

    st.subheader(f"All {group_column.replace('_', ' ')} values")
    st.plotly_chart(
        px.bar(
            category_totals.head(15),
            x=group_column,
            y="abs_amount",
            labels={"abs_amount": "Amount", group_column: group_column.replace("_", " ").title()},
        ),
        use_container_width=True,
    )


def show_rules_editor():
    st.subheader("Grouping rules")
    st.caption("Rows are matched against the description and counterparty, ignoring upper/lower case.")
    edited_rules = st.data_editor(
        st.session_state.rules,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="rules_editor",
    )
    st.session_state.rules = edited_rules


def show_transaction_editor(transactions: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Transactions")
    editable = transactions[
        ["transaction_id", "date", "counterparty", "payment_channel", "description", "amount", "type", "category"]
    ].sort_values("date", ascending=False)
    edited = st.data_editor(
        editable,
        use_container_width=True,
        hide_index=True,
        disabled=["transaction_id", "date", "counterparty", "payment_channel", "description", "amount", "type"],
        key="transactions_editor",
    )
    return edited


def main():
    st.title("Personal Finance Dashboard")
    st.write(
        "Upload a bank export, map its columns once, and explore your income and expenses with editable groups."
    )

    initialize_rules()

    uploaded_file = st.file_uploader(
        "Upload your bank export",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is None:
        st.info("Upload a CSV or Excel file to get started.")
        return

    try:
        raw_df = read_uploaded_file(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the file: {exc}")
        return

    if raw_df.empty:
        st.warning("The uploaded file is empty.")
        return

    selection = build_column_selection(raw_df)
    transactions = prepare_transactions(raw_df, selection)

    if transactions.empty:
        st.warning("No valid transactions were found after parsing the selected columns.")
        return

    filtered = apply_rules(transactions, st.session_state.rules)

    with st.sidebar:
        st.header("Filters")
        available_months = sorted(filtered["month"].dropna().unique().tolist(), reverse=True)
        selected_month = st.selectbox(
            "Month",
            available_months,
            index=0,
        )
        filtered = filtered[filtered["month"] == selected_month]
        available_categories = sorted(filtered["category"].unique().tolist())
        selected_categories = st.multiselect(
            "Categories",
            available_categories,
            default=available_categories,
        )
        group_column = st.selectbox(
            "Group charts by",
            ["category", "counterparty", "payment_channel"],
            format_func=lambda value: value.replace("_", " ").title(),
        )

    if selected_categories:
        filtered = filtered[filtered["category"].isin(selected_categories)]

    show_rules_editor()

    edited_transactions = show_transaction_editor(filtered)
    if {"transaction_id", "category"}.issubset(edited_transactions.columns):
        st.session_state.manual_categories.update(
            dict(zip(edited_transactions["transaction_id"], edited_transactions["category"]))
        )
        filtered = filtered.copy()
        filtered["category"] = filtered["transaction_id"].map(st.session_state.manual_categories).fillna(
            filtered["category"]
        )

    show_summary(filtered)
    show_charts(filtered, group_column, selected_month)

    st.subheader(f"{group_column.replace('_', ' ').title()} summary")
    summary = (
        filtered.groupby([group_column, "type"], as_index=False)["abs_amount"]
        .sum()
        .sort_values(["type", "abs_amount"], ascending=[True, False])
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
