"""
interactive.py — prompts
Terminal prompts for any run configuration the user didn't supply via
CLI flags. Flags always win; a prompt only fires for whatever's still
missing after argument parsing. In --yes (non-interactive) mode, none
of these are called at all — main.py raises a clear error instead if
something required is still missing.

Uses questionary for arrow-key menus and multi-select checklists.
"""

import questionary


def prompt_for_path() -> str:
    return questionary.path("Path to your data file (CSV, Excel, or JSON):").ask()


def prompt_for_multi_sheet_mode() -> str:
    """Only relevant when more than one sheet will be read. Returns a
    column name to merge sheets on, or None to stack rows (the default,
    correct choice when sheets genuinely share the same row layout —
    e.g. the same clean export split across years)."""
    choice = questionary.select(
        "Multiple sheets will be read. How should they be combined?",
        choices=[
            questionary.Choice("Stack rows (sheets share the same layout)", value=None),
            questionary.Choice("Merge side-by-side on a shared key column "
                                "(e.g. each sheet is a different topic, same District)", value="merge"),
        ],
    ).ask()
    if choice != "merge":
        return None
    return questionary.text("Which column should the sheets be merged on? (e.g. District)").ask()


def prompt_for_sheets(sheet_names: list) -> list:
    """Checklist of Excel sheets, all pre-checked (matches the 'read
    all sheets' default) so the user can narrow it down instead."""
    if not sheet_names:
        return None
    choices = [questionary.Choice(name, checked=True) for name in sheet_names]
    selected = questionary.checkbox(
        "Which sheet(s) should be read? (all selected by default)", choices=choices
    ).ask()
    # Empty selection or "everything selected" both mean "no restriction".
    if not selected or set(selected) == set(sheet_names):
        return None
    return selected


def prompt_for_show_group_table() -> bool:
    """Whether to print the grouped summary table in the terminal at
    all (beyond its shape) — independent of the column-detail prompt,
    since a narrow grouped table still prints in full by default even
    when detailed per-column stats were declined."""
    return questionary.confirm(
        "Print the grouped summary table in the terminal? "
        "(it's always saved in full to the report file either way)",
        default=True,
    ).ask()


def prompt_for_group_by(categorical_columns: list) -> str:
    """Returns a column name to group by, or None to skip aggregation."""
    if not categorical_columns:
        return None
    options = categorical_columns + ["Skip aggregation"]
    choice = questionary.select(
        "Which column should rows be grouped by?", choices=options
    ).ask()
    return None if choice == "Skip aggregation" else choice


def prompt_for_column_details(all_columns: list) -> list:
    """Asks whether the user wants full stats printed for specific
    columns, beyond the terminal's default summary-only view. Uses a
    text prompt (not a checkbox) since a wide dataset can have hundreds
    of columns — scrolling a checkbox list that long is worse than
    letting the user type names they already saw printed above."""
    want_details = questionary.confirm(
        "Show detailed stats for specific columns? (full stats for every "
        "column are always saved to the report file regardless)",
        default=False,
    ).ask()
    if not want_details:
        return []

    names = questionary.autocomplete(
        "Type column names one at a time (Enter on blank to finish):",
        choices=all_columns,
    ).ask()
    # questionary.autocomplete returns a single answer per call; loop
    # until the user submits blank.
    selected = []
    if names:
        selected.append(names)
    while names:
        names = questionary.autocomplete(
            "Add another column (blank to finish):", choices=all_columns
        ).ask()
        if names:
            selected.append(names)
    return selected


def prompt_for_stats() -> list:
    """Returns a list of stat types to include, e.g. ['describe', 'rank', 'outliers']."""
    choices = [
        questionary.Choice("Descriptive stats (mean/median/std/etc. per column)", value="describe", checked=True),
        questionary.Choice("Top/bottom-N ranking", value="rank"),
        questionary.Choice("Outlier detection", value="outliers"),
    ]
    return questionary.checkbox("Which stats should the report include?", choices=choices).ask()


def prompt_for_metric_column(numeric_columns: list, purpose: str) -> str:
    """Asks which numeric column to rank/detect-outliers on, when --metric wasn't given."""
    if not numeric_columns:
        return None
    return questionary.select(f"Which column should {purpose} use?", choices=numeric_columns).ask()


def prompt_for_export() -> tuple:
    """Returns (format, path) where format is 'csv', 'json', 'html', or None to skip."""
    fmt = questionary.select(
        "Export the report?", choices=["CSV", "JSON", "HTML", "PDF", "Skip export"]
    ).ask()
    if fmt == "Skip export":
        return None, None
    fmt = fmt.lower()
    path = questionary.path(f"Export path (.{fmt}):").ask()
    return fmt, path
