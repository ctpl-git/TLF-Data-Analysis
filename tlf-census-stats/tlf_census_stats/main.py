"""
main.py — tlf-census-stats CLI
Runs the full census stats report for a supported South Asian country.

Flags are read first; anything not supplied is filled in via
interactive terminal prompts, UNLESS --yes is passed, in which case
any required-but-missing value raises a clear error instead of
prompting (so this can run unattended without hanging on input()).

Usage:
    python -m packages.tlf_census_stats.main
    python -m packages.tlf_census_stats.main --country bangladesh
    python -m packages.tlf_census_stats.main --country india --data path/to/india_census.csv --export path/to/out.csv
    python -m packages.tlf_census_stats.main --country bangladesh --data data/sample/bangladesh_census.xlsx --sheet "Merged_All_Table"
    python -m packages.tlf_census_stats.main --yes --country nepal --data data/sample/nepal_census_2021.csv --export out.csv
"""

import argparse

from .report import StatsReporter
from .loader import CensusLoader
from .country_profiles import COUNTRY_PROFILES
from .errors import ReportWriteError
from . import interactive

# Bundled sample datasets, keyed by country. Add an entry here whenever
# a new sample file is dropped into data/sample/.
# Bundled sample datasets, keyed by country. These are small, clearly
# labeled DEMO fixtures (not real census data) — just enough to let a
# fresh `pip install tlf-census-stats && tlf-census-stats` work with
# zero setup. Resolved via importlib.resources rather than a CWD-relative
# path, so this works correctly whether run from a repo checkout or an
# actual installed package (which may be run from any directory).
import importlib.resources as _resources


def _bundled_sample_path(filename: str) -> str:
    try:
        path = _resources.files("tlf_census_stats").joinpath("data", "sample", filename)
        return str(path) if path.is_file() else None
    except (ModuleNotFoundError, FileNotFoundError):
        return None


DEFAULT_DATA = {
    "nepal": _bundled_sample_path("nepal_census_2021.csv"),
    "bangladesh": _bundled_sample_path("bangladesh_census_2022.csv"),
    "india": _bundled_sample_path("india_from_pdf.csv"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="tlf-census-stats Runner")
    parser.add_argument(
        "--country", default=None, choices=sorted(COUNTRY_PROFILES),
        help="Which country's census schema to use. Default: prompted, or 'nepal' in --yes mode.",
    )
    parser.add_argument(
        "--data", default=None,
        help="Path to a census file (CSV, Excel, or JSON). Defaults to the bundled sample for --country, if one exists.",
    )
    parser.add_argument("--sheet", default=None, action="append",
                         help="Excel sheet name to read (repeatable for multiple). Default: all sheets.")
    parser.add_argument("--merge-on", default=None,
                         help="When reading multiple sheets, merge them side-by-side on this shared "
                              "column instead of stacking rows (e.g. --merge-on District).")
    parser.add_argument(
        "--export", default=None,
        help="Path to export the region-level summary CSV.",
    )
    parser.add_argument("--yes", action="store_true",
                         help="Non-interactive mode: never prompt, error on missing required values.")
    return parser.parse_args()


def _require(value, flag_name):
    if value is None:
        raise SystemExit(f"--yes was given but {flag_name} was not provided and is required.")
    return value


def main():
    args = parse_args()

    # --- country ---
    country = args.country
    if country is None:
        country = "nepal" if args.yes else interactive.prompt_for_country(list(COUNTRY_PROFILES))

    # --- data path ---
    data_path = args.data or DEFAULT_DATA.get(country)
    if data_path is None:
        if args.yes:
            _require(None, "--data")
        data_path = interactive.prompt_for_path()

    # --- sheet selection (Excel only) ---
    sheet = args.sheet
    available_sheets = CensusLoader(data_path, country=country).list_sheets()
    if available_sheets and sheet is None and not args.yes:
        sheet = interactive.prompt_for_sheets(available_sheets)
    # argparse --sheet with action="append" gives a list or None;
    # a single-item list is passed through as-is (valid for CensusLoader).

    # --- how to combine multiple sheets (only relevant if >1 will be read) ---
    sheet_count = len(sheet) if isinstance(sheet, list) else (len(available_sheets) if sheet is None else 1)
    merge_on = args.merge_on
    if merge_on is None and sheet_count > 1 and not args.yes:
        merge_on = interactive.prompt_for_multi_sheet_mode()
    # In --yes mode with multiple sheets and no --merge-on: defaults to
    # stacking rows, same as the single-sheet/no-flag behavior.

    reporter = StatsReporter(data_path, country=country, sheet=sheet, merge_on=merge_on)
    try:
        reporter.run()
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(f"[StatsReporter] {e}")

    # --- export ---
    export_path = args.export
    if export_path is None and not args.yes:
        export_path = interactive.prompt_for_export()
    if export_path:
        try:
            reporter.export(export_path)
        except ReportWriteError as e:
            raise SystemExit(f"[StatsReporter] {e}")


if __name__ == "__main__":
    main()

