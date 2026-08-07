"""
interactive.py — prompts
Terminal prompts for any run configuration not supplied via CLI flags,
matching the same flags-first pattern as tlf-statistical-summary: a
prompt only fires for whatever's still missing after argument parsing,
and none of these are called at all in --yes (non-interactive) mode —
main.py raises a clear error instead if something required is missing.

Uses questionary for arrow-key menus and multi-select checklists.
"""

import questionary


def prompt_for_country(country_codes: list) -> str:
    return questionary.select("Which country's census schema should be used?",
                               choices=sorted(country_codes)).ask()


def prompt_for_path() -> str:
    return questionary.path("Path to your census data file (CSV, Excel, or JSON):").ask()


def prompt_for_multi_sheet_mode() -> str:
    """Only relevant when more than one sheet will be read. Returns a
    column name to merge sheets on, or None to stack rows (the default,
    correct choice when sheets genuinely share the same row layout)."""
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
    if not selected or set(selected) == set(sheet_names):
        return None
    return selected


def prompt_for_export() -> str:
    """Returns an export path, or None to skip export. Format (CSV,
    JSON, or HTML) is inferred from the extension typed here."""
    want_export = questionary.confirm("Export the full report? (.csv, .json, .html, or .pdf)", default=True).ask()
    if not want_export:
        return None
    return questionary.path("Export path (e.g. report.csv, report.html, report.pdf):").ask()
