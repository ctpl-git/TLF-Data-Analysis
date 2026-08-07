"""
report.py — Reporter
Orchestrates the generic pipeline: load -> profile columns -> describe
-> (optional) rank / outliers / group-by aggregation -> export.
Every domain-specific choice (which column to group by, which numeric
column to rank/outlier-check, which stats to run at all) is passed in
explicitly rather than assumed, since this package has no schema to
infer them from.

Terminal output stays short and readable no matter how wide the
dataset is (some real-world exports have hundreds of columns): only a
summary prints by default, with full per-column detail optionally
requested for specific columns. A complete report — every column, in
full — is always written to a file automatically, regardless of
whether an --export was requested, so nothing is ever only visible in
a terminal that scrolled past it.
"""

from pathlib import Path
import json

import pandas as pd

from .loader import TabularLoader
from .profiler import ColumnProfiler
from .describe import Describer
from .rank import Ranker
from .outlier import OutlierDetector
from .aggregate import Aggregator
from .errors import ReportWriteError, open_for_write

# Above this many columns, wide tables (grouped summary, rank, outliers)
# print only their shape to the terminal instead of the full table —
# the full table is still always in the auto-written report file.
WIDE_TABLE_COLUMN_THRESHOLD = 15


class Reporter:
    """
    Usage:
        reporter = Reporter("weather.csv")
        reporter.load()
        reporter.run(
            stats=["describe", "rank", "outliers"],
            group_by="station",
            metric_column="rainfall_mm",
            detail_columns=["rainfall_mm"],  # optional: full stats on request
        )
        reporter.export("csv", "report.csv")
    """

    def __init__(self, filepath: str, sheet=None, merge_on: str = None):
        self.filepath = filepath
        self.sheet = sheet
        self.merge_on = merge_on
        self.df = None
        self.profile = None
        self._group_summary = None
        self._rank_result = None
        self._outlier_result = None

    def load(self) -> pd.DataFrame:
        self.df = TabularLoader(self.filepath, sheet=self.sheet, merge_on=self.merge_on).load()
        self.profile = ColumnProfiler(self.df).profile()
        return self.df

    def run(self, stats: list, group_by: str = None, metric_column: str = None,
            top_n: int = 5, agg: str = "sum", detail_columns: list = None,
            label_column: str = None, report_path: str = None,
            show_group_table: bool = True):
        if self.df is None:
            self.load()

        # A label column keeps rank/outlier output to two columns
        # instead of dumping every column in the row — defaults to the
        # first categorical column found (e.g. a name/id/station field).
        if label_column is None and self.profile.categorical_columns:
            label_column = self.profile.categorical_columns[0]

        self.profile.print_summary()
        print()

        describer = Describer(self.df, self.profile)

        if "describe" in stats:
            if detail_columns:
                describer.print_report(columns=detail_columns)
                print()

        if group_by:
            self._group_summary = Aggregator(self.df).group_by(group_by, agg=agg)
            print(f"[Aggregator] Grouped by {group_by!r} ({agg}): "
                  f"{self._group_summary.shape[0]} rows x {self._group_summary.shape[1]} columns")
            if show_group_table and self._group_summary.shape[1] <= WIDE_TABLE_COLUMN_THRESHOLD:
                print(self._group_summary.to_string(index=False))
            elif not show_group_table:
                print("    (table printing skipped — see the full report file)")
            else:
                print("    (too many columns to print here — see the full report file)")
            print()

        if "rank" in stats and metric_column:
            ranker = Ranker(self.df)
            self._rank_result = ranker.top(top_n, by=metric_column, label_column=label_column)
            print(f"[Ranker] Top {top_n} by {metric_column!r}:")
            print(self._rank_result.to_string(index=False))
            print()

        if "outliers" in stats and metric_column:
            detector = OutlierDetector(self.df)
            self._outlier_result = detector.detect(by=metric_column, label_column=label_column)
            print(f"[OutlierDetector] {len(self._outlier_result)} outlier row(s) on {metric_column!r}:")
            if not self._outlier_result.empty:
                print(self._outlier_result.to_string(index=False))
            print()

        # Always write the complete report to a file — this is where
        # every column's full stats live, regardless of what printed
        # above or whether --export was used for the main data export.
        report_path = report_path or self._default_report_path()
        self._write_full_report(describer, report_path)
        print(f"[Reporter] Full column-by-column report saved to {report_path}")

    def _default_report_path(self) -> str:
        stem = Path(self.filepath).stem
        return str(Path(self.filepath).parent / f"{stem}_full_report.txt")

    def _write_full_report(self, describer: Describer, path: str):
        describer.write_full_report(path)
        # Append the wide tables too, in full, regardless of the
        # terminal's column-count cutoff.
        with open_for_write(path, "a", encoding="utf-8") as f:
            if self._group_summary is not None:
                f.write("\nGrouped summary\n" + "=" * 60 + "\n")
                f.write(self._group_summary.to_string(index=False))
                f.write("\n")
            if self._rank_result is not None:
                f.write("\nRanking\n" + "=" * 60 + "\n")
                f.write(self._rank_result.to_string(index=False))
                f.write("\n")
            if self._outlier_result is not None:
                f.write("\nOutliers\n" + "=" * 60 + "\n")
                f.write(self._outlier_result.to_string(index=False))
                f.write("\n")

    def export(self, fmt: str, path: str, chart_columns: list = None):
        """Exports every result table this run produced — grouped
        summary, ranking, outliers — not just one, so the export
        matches what the full report file shows rather than being a
        narrower subset of it. Falls back to the raw loaded data if
        none of those were run (e.g. describe-only, no group-by).

        fmt="html" builds a single self-contained HTML file with tables
        and embedded charts instead — see html_report.py. chart_columns
        (only relevant for html) selects which columns get their own
        chart; otherwise a small default set is charted automatically."""
        if fmt == "html":
            from .html_report import HtmlReportBuilder
            HtmlReportBuilder(self, chart_columns=chart_columns).write(path)
            print(f"[Reporter] HTML report exported to {path}")
            return

        if fmt == "pdf":
            from .html_report import HtmlReportBuilder
            HtmlReportBuilder(self, chart_columns=chart_columns).write_pdf(path)
            print(f"[Reporter] PDF report exported to {path}")
            return

        sections = []
        if self._group_summary is not None:
            sections.append(("Grouped summary", self._group_summary))
        if self._rank_result is not None:
            sections.append(("Ranking", self._rank_result))
        if self._outlier_result is not None:
            sections.append(("Outliers", self._outlier_result))
        if not sections:
            sections.append(("Data", self.df))

        if fmt == "csv":
            with open_for_write(path, "w", encoding="utf-8", newline="") as f:
                for i, (title, data) in enumerate(sections):
                    if i > 0:
                        f.write("\n")
                    f.write(f"{title}\n")
                    data.to_csv(f, index=False)
        elif fmt == "json":
            payload = {
                title.lower().replace(" ", "_"): json.loads(data.to_json(orient="records"))
                for title, data in sections
            }
            with open_for_write(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {fmt}")
        print(f"[Reporter] Exported to {path} ({', '.join(title for title, _ in sections)})")
