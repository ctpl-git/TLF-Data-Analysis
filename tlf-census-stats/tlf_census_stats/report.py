"""
report.py — StatsReporter
Combines all stats modules into a single printable or exportable
report. Works for any supported country by name (see
country_profiles.py); headers and labels adapt to that country's
region/subregion terminology.
"""

import json

import pandas as pd
from .loader import CensusLoader
from .describe import DataDescriber
from .aggregate import RegionAggregator
from .rank import SubregionRanker
from .outlier import OutlierDetector
from .errors import ReportWriteError, open_for_write


class StatsReporter:
    """
    Orchestrates all stats modules and produces a complete analysis report.

    Usage:
        reporter = StatsReporter("data/sample/nepal_census_2021.csv", country="nepal")
        reporter.run()
        reporter.export("output/nepal_region_summary.csv")
    """

    def __init__(self, filepath: str, country: str = "nepal", sheet=None, merge_on: str = None):
        self.filepath = filepath
        self.country = country
        self.sheet = sheet
        self.merge_on = merge_on
        self.df = None
        self.profile = None
        self._results = {}

    def run(self):
        """Run the full stats pipeline and print results."""
        # Load
        loader = CensusLoader(self.filepath, country=self.country, sheet=self.sheet, merge_on=self.merge_on)
        self.df = loader.load()
        self.profile = loader.profile

        describer = DataDescriber(self.df)
        aggregator = RegionAggregator(self.df)
        ranker = SubregionRanker(self.df)
        outlier = OutlierDetector(self.df)

        region_label = self.profile.region_label
        subregion_label = self.profile.subregion_label

        # 1. National Totals
        totals = describer.national_totals()
        self._results["national_totals"] = totals
        print("\n" + "="*55)
        print(f"  {self.profile.country_name.upper()} CENSUS — NATIONAL OVERVIEW")
        print("="*55)
        for k, v in totals.items():
            print(f"  {k:<30} {v:>15,}" if isinstance(v, int) else f"  {k:<30} {v:>15}")

        # 2. Descriptive Summary
        print("\n" + "="*55)
        print("  DESCRIPTIVE STATISTICS")
        print("="*55)
        summary = describer.summary()
        self._results["descriptive_summary"] = summary
        print(summary.to_string())

        # 3. Region Summary
        print("\n" + "="*55)
        print(f"  {region_label.upper()}-LEVEL SUMMARY")
        print("="*55)
        region = aggregator.aggregate()
        self._results["region_summary"] = region
        display_cols = [c for c in ["region", "total_population", "subregion_count",
                                     "avg_literacy_rate", "urbanization_pct"] if c in region.columns]
        print(region[display_cols].to_string(index=False))

        # 4. Rankings
        print("\n" + "="*55)
        print(f"  TOP 5 {subregion_label.upper()}S BY POPULATION")
        print("="*55)
        top5_pop = ranker.top(5, by="total_population")
        self._results["top5_population"] = top5_pop
        print(top5_pop.to_string(index=False))

        if "literacy_rate" in self.df.columns:
            print("\n" + "="*55)
            print(f"  TOP 5 {subregion_label.upper()}S BY LITERACY RATE")
            print("="*55)
            top5_lit = ranker.top(5, by="literacy_rate")
            self._results["top5_literacy"] = top5_lit
            print(top5_lit.to_string(index=False))

            print("\n" + "="*55)
            print(f"  BOTTOM 5 {subregion_label.upper()}S BY LITERACY RATE")
            print("="*55)
            bot5_lit = ranker.bottom(5, by="literacy_rate")
            self._results["bottom5_literacy"] = bot5_lit
            print(bot5_lit.to_string(index=False))
        else:
            print(f"\n[StatsReporter] Skipping literacy-rate rankings — "
                  f"not present in {self.profile.country_name}'s data.")

        # 5. Outliers
        print("\n" + "="*55)
        print("  OUTLIER DETECTION SUMMARY")
        print("="*55)
        outlier_summary = outlier.summary()
        self._results["outlier_summary"] = outlier_summary
        print(outlier_summary.to_string(index=False))

        print("\n[StatsReporter] Report complete.\n")

    def export(self, output_path: str):
        """Exports every result this run produced — national totals,
        descriptive stats, region summary, rankings, outliers — not
        just the region summary, so the export matches what actually
        printed to the terminal. Format (CSV, JSON, or HTML) is
        inferred from output_path's extension; defaults to CSV if none
        of those match.

        HTML output builds a single self-contained file with tables and
        embedded charts (region population bars, gender composition,
        top-N rankings) — see html_report.py. PDF is the same report
        rendered to PDF via xhtml2pdf (pure Python, no system deps)."""
        if not self._results:
            raise RuntimeError("Run .run() before exporting.")

        if str(output_path).lower().endswith(".html"):
            from .html_report import HtmlReportBuilder
            HtmlReportBuilder(self).write(output_path)
            print(f"[StatsReporter] HTML report exported to {output_path}")
            return
        if str(output_path).lower().endswith(".pdf"):
            from .html_report import HtmlReportBuilder
            HtmlReportBuilder(self).write_pdf(output_path)
            print(f"[StatsReporter] PDF report exported to {output_path}")
            return

        # national_totals is a dict, not a DataFrame — wrap it as a
        # small two-column table so it fits alongside everything else.
        sections = []
        for key, value in self._results.items():
            title = key.replace("_", " ").title()
            if isinstance(value, dict):
                value = pd.DataFrame(list(value.items()), columns=["metric", "value"])
            elif not (isinstance(value.index, pd.RangeIndex) or pd.api.types.is_integer_dtype(value.index)):
                # Some tables (e.g. descriptive_summary) carry their row
                # labels in the index rather than a column — reset_index
                # so those labels survive to_csv/to_json instead of being
                # silently dropped. Tables that were merely sorted (e.g.
                # region_summary, ranked by population) keep an integer
                # index — just reordered, not meaningful — so those are
                # left as-is; to_csv(index=False) already omits a
                # non-meaningful integer index correctly on its own.
                value = value.reset_index().rename(columns={"index": "metric"})
            sections.append((title, value))

        fmt = "json" if str(output_path).lower().endswith(".json") else "csv"

        if fmt == "csv":
            with open_for_write(output_path, "w", encoding="utf-8", newline="") as f:
                for i, (title, data) in enumerate(sections):
                    if i > 0:
                        f.write("\n")
                    f.write(f"{title}\n")
                    data.to_csv(f, index=False)
        else:
            payload = {}
            for title, data in sections:
                key = title.lower().replace(" ", "_")
                if title == "National Totals":
                    payload[key] = dict(zip(data["metric"], data["value"]))
                else:
                    payload[key] = json.loads(data.to_json(orient="records"))
            with open_for_write(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

        print(f"[StatsReporter] Full report exported to {output_path} "
              f"({', '.join(title for title, _ in sections)})")

    def get(self, key: str) -> pd.DataFrame:
        """Retrieve a specific result by key."""
        return self._results.get(key)
