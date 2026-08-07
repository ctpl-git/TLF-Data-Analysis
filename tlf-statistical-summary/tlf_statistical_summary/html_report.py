"""
html_report.py — HtmlReportBuilder
Builds a single self-contained HTML report (tables + embedded chart
images, no external files/CDN dependencies) from a Reporter's results.
Charts are generated with matplotlib and embedded as base64 PNGs, so
the resulting .html file can be opened, emailed, or shared as one file.

Chart generation is capped for wide datasets — hundreds of columns
would make an enormous, slow-to-render file. By default only a small
number of numeric columns get their own chart; pass detail_columns to
choose exactly which ones do instead.
"""

import base64
import io

import matplotlib
matplotlib.use("Agg")  # no display backend needed — this only renders to PNG bytes
import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CHART_COLUMN_CAP = 8


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _histogram(series: pd.Series, title: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.hist(series.dropna(), bins=20, color="#4C72B0", edgecolor="white")
    ax.set_title(title, fontsize=11)
    ax.set_ylabel("count")
    return _fig_to_base64(fig)


def _category_bar(series: pd.Series, title: str, top_n: int = 12) -> str:
    counts = series.value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(counts.index.astype(str), counts.values, color="#55A868")
    ax.set_title(title, fontsize=11)
    ax.set_ylabel("count")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return _fig_to_base64(fig)


def _grouped_bar(df: pd.DataFrame, label_col: str, value_col: str, title: str, top_n: int = 15) -> str:
    top = df.nlargest(top_n, value_col)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(top[label_col].astype(str), top[value_col], color="#C44E52")
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(value_col)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return _fig_to_base64(fig)


def _table_html(df: pd.DataFrame, max_rows: int = None) -> str:
    if max_rows and len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_html(classes="data-table", index=False, border=0, na_rep="—")


_CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       margin: 2rem auto; max-width: 1000px; color: #1a1a1a; line-height: 1.5; }
h1 { font-size: 1.6rem; border-bottom: 2px solid #333; padding-bottom: .3rem; }
h2 { font-size: 1.2rem; margin-top: 2.2rem; color: #333; }
.meta { color: #666; font-size: .9rem; margin-bottom: 1.5rem; }
.data-table { border-collapse: collapse; width: 100%; font-size: .85rem; margin: .8rem 0 1.5rem; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; text-align: right; }
.data-table th { background: #f2f2f2; text-align: center; }
.data-table td:first-child, .data-table th:first-child { text-align: left; }
.chart { margin: 1rem 0; }
.chart img { max-width: 100%; }
.note { color: #888; font-size: .8rem; font-style: italic; }
"""


class HtmlReportBuilder:
    def __init__(self, reporter, chart_columns: list = None, chart_cap: int = DEFAULT_CHART_COLUMN_CAP):
        self.reporter = reporter
        self.chart_columns = chart_columns
        self.chart_cap = chart_cap

    def build(self) -> str:
        r = self.reporter
        parts = [f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"]
        parts.append(f"<h1>Statistical Summary Report</h1>")
        parts.append(f"<div class='meta'>Source: {r.filepath} &nbsp;|&nbsp; "
                      f"{len(r.profile.columns)} columns, {len(r.df)} rows</div>")

        parts.append(self._section_overview())
        parts.append(self._section_charts())
        if r._group_summary is not None:
            parts.append(self._section_group_summary())
        if r._rank_result is not None:
            parts.append(self._section_ranking())
        if r._outlier_result is not None:
            parts.append(self._section_outliers())

        parts.append("</body></html>")
        return "\n".join(parts)

    def write(self, path: str):
        from .errors import open_for_write
        html = self.build()
        with open_for_write(path, "w", encoding="utf-8") as f:
            f.write(html)

    def write_pdf(self, path: str):
        """Converts the same HTML report to a PDF file via xhtml2pdf —
        a pure-Python HTML-to-PDF converter with no system-level
        dependencies (unlike e.g. WeasyPrint, which needs Cairo/Pango
        installed separately — painful on Windows). Same tables and
        charts as the HTML version, just paginated."""
        from .errors import open_for_write, ReportWriteError
        from xhtml2pdf import pisa

        html = self.build()
        try:
            with open_for_write(path, "wb") as f:
                result = pisa.CreatePDF(html, dest=f)
        except ReportWriteError:
            raise
        if result.err:
            raise ReportWriteError(
                f"Couldn't render PDF to '{path}' — xhtml2pdf reported {result.err} error(s) "
                f"while converting the report's HTML."
            )

    def _section_overview(self) -> str:
        r = self.reporter
        rows = [{
            "column": c.name, "type": c.dtype,
            "unique": c.unique_count, "missing": c.missing_count,
        } for c in r.profile.columns]
        table = _table_html(pd.DataFrame(rows))
        return f"<h2>Column Overview</h2>{table}"

    def _section_charts(self) -> str:
        r = self.reporter
        if self.chart_columns:
            columns = [c for c in self.chart_columns if c in r.df.columns]
            note = ""
        else:
            columns = r.profile.numeric_columns[: self.chart_cap]
            total_numeric = len(r.profile.numeric_columns)
            note = (f"<p class='note'>Showing charts for {len(columns)} of {total_numeric} numeric "
                    f"columns. Pass specific columns to chart all of them.</p>"
                    if total_numeric > len(columns) else "")

        html = ["<h2>Column Charts</h2>", note]
        profile_by_name = {c.name: c for c in r.profile.columns}
        for col in columns:
            dtype = profile_by_name[col].dtype if col in profile_by_name else "numeric"
            if dtype == "categorical":
                img = _category_bar(r.df[col], col)
            else:
                img = _histogram(r.df[col], col)
            html.append(f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>")
        return "\n".join(html)

    def _section_group_summary(self) -> str:
        r = self.reporter
        html = [f"<h2>Grouped Summary</h2>"]
        table = _table_html(r._group_summary, max_rows=200)
        html.append(table)
        if len(r._group_summary) > 200:
            html.append(f"<p class='note'>Showing first 200 of {len(r._group_summary)} rows.</p>")
        # chart it only if narrow enough to pick a sensible metric column
        numeric_cols = r._group_summary.select_dtypes(include="number").columns.tolist()
        label_cols = [c for c in r._group_summary.columns if c not in numeric_cols]
        if numeric_cols and label_cols:
            img = _grouped_bar(r._group_summary, label_cols[0], numeric_cols[0],
                                f"Top by {numeric_cols[0]}")
            html.append(f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>")
        return "\n".join(html)

    def _section_ranking(self) -> str:
        r = self.reporter
        table = _table_html(r._rank_result)
        numeric_cols = r._rank_result.select_dtypes(include="number").columns.tolist()
        label_cols = [c for c in r._rank_result.columns if c not in numeric_cols]
        chart = ""
        if numeric_cols and label_cols:
            img = _grouped_bar(r._rank_result, label_cols[0], numeric_cols[0], "Ranking")
            chart = f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>"
        return f"<h2>Ranking</h2>{table}{chart}"

    def _section_outliers(self) -> str:
        r = self.reporter
        table = _table_html(r._outlier_result)
        return f"<h2>Outliers</h2>{table}"
