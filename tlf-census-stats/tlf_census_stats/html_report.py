"""
html_report.py — HtmlReportBuilder
Builds a single self-contained HTML report (tables + embedded chart
images) from a StatsReporter's results, after .run() has populated
self._results. Mirrors tlf-statistical-summary's html_report.py, but
tailored to this package's fixed census-report shape (national totals,
region summary, rankings, outliers) rather than a generic column list.
"""

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _bar_chart(labels, values, title: str, color: str = "#4C72B0") -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([str(l) for l in labels], values, color=color)
    ax.set_title(title, fontsize=11)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return _fig_to_base64(fig)


def _stacked_gender_chart(df: pd.DataFrame, label_col: str, title: str) -> str:
    """Stacked bar of male/female/(third_gender if present) per row."""
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = df[label_col].astype(str)
    bottom = [0] * len(df)
    for col, color in [("male", "#4C72B0"), ("female", "#C44E52"), ("third_gender", "#55A868")]:
        if col not in df.columns:
            continue
        ax.bar(labels, df[col], bottom=bottom, label=col, color=color)
        bottom = [b + v for b, v in zip(bottom, df[col])]
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8)
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
    def __init__(self, reporter):
        self.reporter = reporter

    def build(self) -> str:
        r = self.reporter
        if not r._results:
            raise RuntimeError("Run .run() before building an HTML report.")

        region_label = r.profile.region_label
        subregion_label = r.profile.subregion_label

        parts = [f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"]
        parts.append(f"<h1>{r.profile.country_name} Census Report</h1>")
        parts.append(f"<div class='meta'>Source: {r.filepath} &nbsp;|&nbsp; "
                      f"{len(r.df)} {subregion_label.lower()}s across "
                      f"{r.df['region'].nunique()} {region_label.lower()}s</div>")

        parts.append(self._section_national_totals())
        parts.append(self._section_descriptive_summary())
        parts.append(self._section_region_summary(region_label))
        parts.append(self._section_gender_composition())
        parts.append(self._section_rankings(subregion_label))
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
        installed separately — painful on Windows)."""
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

    def _section_national_totals(self) -> str:
        totals = self.reporter._results["national_totals"]
        table = _table_html(pd.DataFrame(list(totals.items()), columns=["metric", "value"]))
        return f"<h2>National Totals</h2>{table}"

    def _section_descriptive_summary(self) -> str:
        summary = self.reporter._results["descriptive_summary"]
        table = _table_html(summary.reset_index().rename(columns={"index": "metric"}))
        return f"<h2>Descriptive Statistics</h2>{table}"

    def _section_region_summary(self, region_label: str) -> str:
        region = self.reporter._results["region_summary"]
        table = _table_html(region)
        html = [f"<h2>{region_label}-Level Summary</h2>", table]
        if "total_population" in region.columns:
            img = _bar_chart(region["region"], region["total_population"],
                              f"Total Population by {region_label}")
            html.append(f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>")
        return "\n".join(html)

    def _section_gender_composition(self) -> str:
        region = self.reporter._results["region_summary"]
        if "male" not in region.columns or "female" not in region.columns:
            return ""
        img = _stacked_gender_chart(region, "region", "Gender Composition by Region")
        return f"<h2>Gender Composition</h2><div class='chart'><img src='data:image/png;base64,{img}'/></div>"

    def _section_rankings(self, subregion_label: str) -> str:
        r = self.reporter
        html = []
        if "top5_population" in r._results:
            top5 = r._results["top5_population"]
            table = _table_html(top5)
            img = _bar_chart(top5["subregion"], top5["total_population"],
                              f"Top 5 {subregion_label}s by Population")
            html.append(f"<h2>Top 5 {subregion_label}s by Population</h2>{table}"
                        f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>")
        if "top5_literacy" in r._results:
            top5_lit = r._results["top5_literacy"]
            table = _table_html(top5_lit)
            img = _bar_chart(top5_lit["subregion"], top5_lit["literacy_rate"],
                              f"Top 5 {subregion_label}s by Literacy Rate", color="#55A868")
            html.append(f"<h2>Top 5 {subregion_label}s by Literacy Rate</h2>{table}"
                        f"<div class='chart'><img src='data:image/png;base64,{img}'/></div>")
        if "bottom5_literacy" in r._results:
            bot5_lit = r._results["bottom5_literacy"]
            table = _table_html(bot5_lit)
            html.append(f"<h2>Bottom 5 {subregion_label}s by Literacy Rate</h2>{table}")
        return "\n".join(html)

    def _section_outliers(self) -> str:
        outliers = self.reporter._results["outlier_summary"]
        table = _table_html(outliers)
        return f"<h2>Outlier Detection Summary</h2>{table}"
