# tlf-census-stats

Census-specific statistical analysis for South and Southeast Asian countries — part of **TLF** ("The Living Facts").

Loads census data (CSV, Excel, or JSON) for a given country, normalizes it to a canonical schema via per-country column aliasing, and produces national totals, descriptive statistics, region-level aggregation, rankings, outlier detection, and HTML/PDF/CSV/JSON reports — either as a library or an interactive CLI.

Supports: **Nepal, India, Bangladesh, Pakistan, Sri Lanka, Bhutan.**

---

## Install

```bash
pip install tlf-census-stats
```

Or from source, inside the `TLF-Data-Analysis` monorepo:

```bash
cd tlf-census-stats
pip install -e ".[dev]"
```

---

## Canonical schema

Every country profile maps its own raw column names (e.g. Bangladesh's `Division`/`District`, Nepal's `Province`/`District`) onto this canonical shape:

| Column | Required? | Notes |
|---|---|---|
| `region` | Yes | e.g. Division/Province/State |
| `subregion` | Yes | e.g. District |
| `total_population` | Yes | |
| `male` | Yes | |
| `female` | Yes | |
| `households` | Yes | |
| `urban_population` | Optional | |
| `rural_population` | Optional | |
| `literacy_rate` | Optional | |
| `avg_household_size` | Optional | |
| `third_gender` | Optional | A country's non-binary census category (e.g. Bangladesh's "Hijra"). Not every country publishes this. |

A column-check is printed on every load, showing what was actually found vs. expected for that country.

---

## Quickstart (Python API)

```python
from tlf_census_stats import CensusLoader, StatsReporter

# Load and inspect
df = CensusLoader("bangladesh_census.xlsx", country="bangladesh").load()

# Or run the full report pipeline directly
reporter = StatsReporter("bangladesh_census.xlsx", country="bangladesh")
reporter.run()                          # prints national totals, descriptive
                                         # stats, region summary, rankings, outliers
reporter.export("report.html")          # or .csv / .json / .pdf — same content either way
```

### Reading multiple Excel sheets

```python
# Default: read every sheet, stack their rows into one DataFrame
df = CensusLoader("census.xlsx", country="bangladesh").load()

# Read just one/some sheets
df = CensusLoader("census.xlsx", country="bangladesh", sheet="Merged_All_Table").load()

# Combine several single-topic sheets side-by-side on a shared key,
# instead of stacking rows (use this when each sheet is a different
# topic — household counts, gender split, literacy — all keyed by the
# same District column)
df = CensusLoader("census.xlsx", country="bangladesh", merge_on="District").load()
```

---

## CLI

```bash
tlf-census-stats --country bangladesh --data census.xlsx --export report.html
```

Run with no flags at all for a fully interactive walkthrough (file path → sheet selection → stack-vs-merge → export format):

```bash
tlf-census-stats
```

For unattended/scripted runs, `--yes` disables all prompting and fails loudly (rather than silently guessing) if something required is missing:

```bash
tlf-census-stats --yes --country nepal --data nepal_census.csv --export out.csv
```

Full flag list: `tlf-census-stats --help`

---

## Combining with `tlf-data-cleaning`

Most census data doesn't start out clean — it's published as a PDF. `tlf-data-cleaning` (in the separate `TLF-Data-Manager` repo) handles extraction and cleaning; there's **no runtime dependency** between the two packages, they compose through the canonical CSV shape above.
Three ways data reaches this package:

1. **Already-clean CSV/Excel/JSON** — use `CensusLoader` directly, no other package needed.
2. **Flat-country PDF** (Bangladesh, Pakistan, etc.) — `tlf-data-cleaning`'s `CleaningPipeline` does the whole extract-and-clean step.
3. **India's hierarchical PDF** — `tlf-data-cleaning`'s `PDFTableExtractor` does raw extraction only; this package's `IndiaCensusTransformer` reshapes the nested INDIA → STATE → DISTRICT → SUB-DISTRICT structure into canonical rows (a generic rename/strip/coerce pipeline can't do this reshaping).

Full worked examples for all three: see `tlf-data-cleaning`'s README.

---

## Tests

```bash
pytest tests/ -v
```

`tests/fixtures/` holds small, test-owned sample data (deliberately separate from the demo data bundled with the package itself, in `tlf_census_stats/data/sample/`, which backs the CLI's built-in `--country nepal`/`bangladesh`/`india` defaults).

The India PDF integration test (`test_india_transformer.py`) gracefully skips unless `tlf-data-cleaning` is installed alongside this package and its `tests/fixtures/india_census_sample.pdf` fixture is present at `../../tlf-data-cleaning/tests/fixtures/` — no cross-repo dependency is required for this package's own test suite to pass.
