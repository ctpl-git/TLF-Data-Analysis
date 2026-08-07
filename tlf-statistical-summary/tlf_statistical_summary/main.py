"""
main.py — tlf-statistical-summary CLI
Generic, schema-free descriptive stats for any tabular file.

Usage:
    python main.py --data weather.csv
    python main.py --data weather.xlsx --sheet "Daily Readings" --group-by station --metric rainfall_mm
    python main.py --data weather.csv --yes --stats describe --export csv --export-path out.csv

Flags are read first; anything not supplied is filled in via
interactive terminal prompts, UNLESS --yes is passed, in which case
any required-but-missing value raises a clear error instead of
prompting (so this can run unattended, e.g. from a script or cron job,
without hanging on input()).
"""

import argparse
import sys

from .loader import TabularLoader
from .profiler import ColumnProfiler
from .report import Reporter
from .errors import ReportWriteError
from . import interactive


def parse_args():
    parser = argparse.ArgumentParser(description="tlf-statistical-summary: generic tabular stats")
    parser.add_argument("--data", default=None, help="Path to a CSV, Excel, or JSON file.")
    parser.add_argument("--sheet", default=None, action="append",
                         help="Excel sheet name to read (repeatable for multiple). Default: all sheets.")
    parser.add_argument("--merge-on", default=None,
                         help="When reading multiple sheets, merge them side-by-side on this shared "
                              "column instead of stacking rows (e.g. --merge-on District, when each "
                              "sheet is a different topic keyed by the same district).")
    parser.add_argument("--group-by", default=None, help="Column to group rows by.")
    parser.add_argument("--agg", default="sum", choices=["sum", "mean"], help="Aggregation for --group-by.")
    parser.add_argument("--show-group-table", dest="show_group_table", action="store_true", default=None,
                         help="Print the grouped summary table in the terminal (always saved to the report file regardless).")
    parser.add_argument("--no-group-table", dest="show_group_table", action="store_false",
                         help="Don't print the grouped summary table in the terminal.")
    parser.add_argument("--stats", default=None,
                         help="Comma-separated: describe,rank,outliers. Default: prompted or all if --yes.")
    parser.add_argument("--metric", default=None, help="Numeric column for ranking/outlier detection.")
    parser.add_argument("--label-column", default=None,
                         help="Categorical column used to label rows in rank/outlier output (default: first categorical column found).")
    parser.add_argument("--detail-columns", default=None,
                         help="Comma-separated column names to print full stats for in the terminal. "
                              "Full stats for every column are always saved to the report file regardless.")
    parser.add_argument("--top-n", type=int, default=5, help="N for top/bottom ranking.")
    parser.add_argument("--export", default=None, choices=["csv", "json", "html", "pdf"], help="Export format.")
    parser.add_argument("--export-path", default=None, help="Export file path.")
    parser.add_argument("--yes", action="store_true",
                         help="Non-interactive mode: never prompt, error on missing required values.")
    return parser.parse_args()


def _require(value, flag_name):
    if value is None:
        raise SystemExit(f"--yes was given but {flag_name} was not provided and is required.")
    return value


def main():
    args = parse_args()

    # --- data path ---
    data_path = args.data
    if data_path is None:
        if args.yes:
            _require(None, "--data")
        data_path = interactive.prompt_for_path()

    # --- sheet selection (Excel only) ---
    sheet = args.sheet
    loader = TabularLoader(data_path)
    available_sheets = loader.list_sheets()
    if available_sheets and sheet is None and not args.yes:
        sheet = interactive.prompt_for_sheets(available_sheets)
    # argparse --sheet with action="append" gives a list or None;
    # a single-item list is passed through as-is (list is valid for TabularLoader).

    # --- how to combine multiple sheets (only relevant if >1 will be read) ---
    sheet_count = len(sheet) if isinstance(sheet, list) else (len(available_sheets) if sheet is None else 1)
    merge_on = args.merge_on
    if merge_on is None and sheet_count > 1 and not args.yes:
        merge_on = interactive.prompt_for_multi_sheet_mode()
    # In --yes mode with multiple sheets and no --merge-on: defaults to
    # stacking rows, same as the single-sheet/no-flag behavior.

    reporter = Reporter(data_path, sheet=sheet, merge_on=merge_on)
    reporter.load()

    # --- which stats to run ---
    stats = args.stats.split(",") if args.stats else None
    if stats is None:
        if args.yes:
            stats = ["describe", "rank", "outliers"]
        else:
            stats = interactive.prompt_for_stats()

    # --- group-by ---
    group_by = args.group_by
    if group_by is None and not args.yes:
        group_by = interactive.prompt_for_group_by(reporter.profile.categorical_columns)
    # In --yes mode with no --group-by: aggregation is simply skipped
    # (not a hard requirement — describe/rank/outliers can all run
    # without a group-by column).

    # --- whether to print the grouped table in the terminal ---
    show_group_table = args.show_group_table
    if show_group_table is None:
        if args.yes:
            show_group_table = True
        elif group_by:
            show_group_table = interactive.prompt_for_show_group_table()
        else:
            show_group_table = True

    # --- metric column (needed for rank/outliers) ---
    metric_column = args.metric
    needs_metric = ("rank" in stats or "outliers" in stats)
    if needs_metric and metric_column is None:
        if args.yes:
            _require(None, "--metric (required for rank/outliers in --yes mode)")
        metric_column = interactive.prompt_for_metric_column(
            reporter.profile.numeric_columns, purpose="ranking/outlier detection"
        )

    # --- which columns to show full detail for (terminal only; file always has everything) ---
    detail_columns = args.detail_columns.split(",") if args.detail_columns else None
    if detail_columns is None and not args.yes:
        all_columns = [c.name for c in reporter.profile.columns]
        detail_columns = interactive.prompt_for_column_details(all_columns)

    try:
        reporter.run(
            stats=stats,
            group_by=group_by,
            metric_column=metric_column,
            top_n=args.top_n,
            agg=args.agg,
            detail_columns=detail_columns,
            label_column=args.label_column,
            show_group_table=show_group_table,
        )

        # --- export ---
        export_fmt, export_path = args.export, args.export_path
        if export_fmt is None and not args.yes:
            export_fmt, export_path = interactive.prompt_for_export()
        if export_fmt:
            if export_path is None:
                _require(None, "--export-path")
            reporter.export(export_fmt, export_path, chart_columns=detail_columns)
    except ReportWriteError as e:
        raise SystemExit(f"[Reporter] {e}")


if __name__ == "__main__":
    main()
