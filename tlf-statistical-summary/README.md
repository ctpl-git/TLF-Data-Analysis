# tlf-statistical-summary

Schema-free, generic descriptive statistics for **any** tabular data — part of **TLF** ("The Living Facts").

No fixed columns, no domain assumptions. Reads a CSV, Excel, or JSON file as-is, auto-detects each column's type (numeric / categorical / datetime), and produces descriptive statistics, ranking, outlier detection, and grouped aggregation on whatever columns *you* name at runtime — with an interactive CLI that fills in anything you didn't specify via flags.

**Use this when your data doesn't have a known schema** — weather data, sales data, survey exports, or anything else. For South/Southeast Asian census data with a fixed schema (region/subregion/population/ etc.), see the sibling package `tlf-census-stats` instead.

---

## Install

```bash
pip install tlf-statistical-summary
```

Or from source, inside the `TLF-Data-Analysis` monorepo:

```bash
cd tlf-statistical-summary
pip install -e ".[dev]"
```

---

## Quickstart (Python API)

```python
from tlf_statistical_summary import Reporter

reporter = Reporter("weather.csv")
reporter.load()
reporter.run(
    stats=["describe", "rank", "outliers"],
    group_by="station",
    metric_column="rainfall_mm",
    top_n=5,
)
reporter.export("html", "report.html")   # or "csv" / "json" / "pdf"
```

Terminal output stays short regardless of how many columns the file has — a compact overview by default, with full per-column detail always written to an auto-generated `<file>_full_report.txt`, and optionally printed for specific columns you ask for.

### Reading multiple Excel sheets

```python
from tlf_statistical_summary import TabularLoader

# Default: read every sheet, stack their rows into one DataFrame
df = TabularLoader("data.xlsx").load()

# Read just one/some sheets
df = TabularLoader("data.xlsx", sheet="Daily Readings").load()

# Combine several single-topic sheets side-by-side on a shared key
# instead of stacking rows
df = TabularLoader("data.xlsx", merge_on="District").load()
```

---

## CLI

```bash
tlf-statistical-summary --data weather.csv --group-by station --metric rainfall_mm --stats describe,rank,outliers --export html --export-path report.html
```

Run with no flags at all for a fully interactive walkthrough (file path → sheet selection → which stats → group-by → metric column → export format):

```bash
tlf-statistical-summary
```

For unattended/scripted runs, `--yes` disables all prompting and fails loudly (rather than silently guessing) if something required — like `--metric` when ranking/outlier detection is requested — is missing:

```bash
tlf-statistical-summary --data weather.csv --yes --group-by station --metric rainfall_mm --stats describe,rank --export csv --export-path out.csv
```

Full flag list: `tlf-statistical-summary --help`

---

## What's schema-free actually mean here

There's exactly one place this can't be fully schema-free: grouping. `Aggregator.group_by()` needs to know *which* column to group by, and that can't be reliably auto-detected — so it's always something you supply, either via `--group-by` or the interactive prompt, never inferred from the data.

Everything else — column type detection, descriptive stats, ranking, outlier detection — works on any tabular file with zero configuration.

---

## Tests

```bash
pytest tests/ -v
```

Covers the loader (CSV/Excel/JSON, multi-sheet stacking and merging, PDF rejection), column profiler, describer, ranker, outlier detector, aggregator, the full `Reporter` pipeline (including HTML/PDF/CSV/JSON export and locked-file error handling), and CLI smoke tests for `--yes` mode (full run, missing required flags failing loudly, and group-by correctly being optional).
