# TLF Data Analysis

The analytical core of the TLF pipeline. TLF Data Analysis performs heavy computation and interpretation of data — from descriptive statistics and trend detection to AI-powered insight extraction. It is built as a modular package-first system where each analytical capability is published independently, then composed into a scalable analysis platform.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Python Packages](#python-packages)
- [npm Packages](#npm-packages)
- [Platform Services](#platform-services)
- [Development Roadmap](#development-roadmap)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

TLF Data Analysis transforms raw datasets into actionable intelligence. It is specifically calibrated for South Asian civic, census, and development datasets (SGD/GCE sources) and supports:

- **Descriptive & Inferential Statistics** — Summaries, distributions, hypothesis testing, and regression.
- **Time-Series & Trend Analysis** — Seasonal decomposition, rolling averages, and indicator tracking.
- **Anomaly & Outlier Detection** — ML-based flagging using isolation forests and z-score methods.
- **Cross-Dataset Comparison** — Structural and value-level diffs across data releases.
- **Correlation & Relationship Mining** — Pearson, Spearman, and Kendall across multi-dimensional data.
- **Demographic Profiling** — Segmentation by region, age, gender, and economic sector.
- **NLP Insight Extraction** — Keyword extraction, sentiment analysis, and entity recognition on regional-language text datasets.
- **Visualization & Reporting** — Annotated charts, interactive plots, and exportable HTML/PDF reports.

**Primary Stack:** Python, Bash  
**Categories:** Data, Artificial Intelligence, Computation

---

## Architecture

The project follows a **package-first** design:

```
┌─────────────────────────────────────────────────────────────┐
│                  TLF Data Analysis Platform                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Web UI     │  │   Report     │  │   API Gateway    │   │
│  │  (React)     │  │   Builder    │  │   (FastAPI)      │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         └──────────────────┼───────────────────┘             │
│                            │                                │
│  ┌─────────────────────────┴─────────────────────────────┐  │
│  │            Platform Services (Orchestration)           │  │
│  │  Stats │ Trends │ Anomalies │ Compare │ Correlate │   │  │
│  │  Profile │ Indicators │ NLP │ Visualize │ Reports   │  │  │
│  └─────────────────────────────────────────────────────┘  │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Python pkgs  │  │   npm pkgs   │  │   Storage    │      │
│  │  (Backend)   │  │  (Frontend)  │  │  (DB / S3)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

Each package is **published independently** to PyPI or npm, allowing external projects to consume only the analytical capabilities they need.

---

## Python Packages

| Package | Description | Issue Mapping |
|---------|-------------|---------------|
| `tlf-statistical-summary` | Foundation layer for loading, structuring, and describing data. Generates descriptive stats (mean, median, mode, variance, distribution) calibrated for South Asian civic and census datasets. Handles missing data patterns common in SGD/GCE sources. | #1 Basic data handling, #2 Statistical analysis |
| `tlf-correlation-engine` | Computes Pearson, Spearman, and Kendall correlations across multi-dimensional datasets. Designed for cross-sector analysis such as education vs income in South Asian regions. | #2 Statistical analysis |
| `tlf-trend-detector` | Analyzes time-indexed datasets to identify upward, downward, and cyclical trends. Supports seasonal decomposition and rolling averages relevant to South Asian development indicators. | #4 Advanced analysis techniques |
| `tlf-anomaly-flagger` | Detects statistical anomalies using isolation forests and z-score methods. Flags records for manual review without disrupting the data flow. Serves as the *analysis-side* of data cleaning. | #5 Preprocessing & cleaning |
| `tlf-data-comparator` | Compares two or more versions of a dataset to surface structural and value-level differences. Useful for tracking changes between data releases from civic sources. | #6 Import/export capabilities |
| `tlf-demographic-profiler` | Segments population datasets by demographic variables (age group, gender, geography, economic sector). Produces profiles suitable for policy analysis with built-in chart rendering. | #3 Data visualization |
| `tlf-indicator-tracker` | Monitors key South Asian development indicators (literacy rate, poverty index, etc.) over time, with alerting when indicators cross defined thresholds. | #4 Advanced analysis techniques |
| `tlf-nlp-insight-extractor` | Applies NLP techniques (keyword extraction, sentiment, entity recognition) to unstructured text datasets from South Asian sources. Supports multiple regional languages. | #4 Advanced analysis techniques |
| `tlf-hypothesis-testing` | *(Planned)* Statistical hypothesis testing modules including t-tests, chi-square, ANOVA, and non-parametric tests. | #9 Regression & hypothesis testing |
| `tlf-regression-engine` | *(Planned)* Linear, logistic, and polynomial regression modules for predictive modeling on civic datasets. | #9 Regression & hypothesis testing |
| `tlf-chart-renderer` | *(Planned)* Programmatic chart generation engine producing static and interactive visualizations (matplotlib, plotly, altair). | #3, #10 Visualization modules |
| `tlf-timeseries-viz` | *(Planned)* Interactive time-series visualization components with zoom, pan, and annotation support. | #10 Timeseries visualization |
| `tlf-report-generator` | *(Planned)* HTML/PDF report assembler combining stats, charts, and narrative insights into policy-ready documents. | #3 Visualization & reporting |
| `tlf-io-formats` | Import/export handlers for CSV, JSON, Excel, and Parquet with streaming support for large civic datasets. | #6 Import/export capabilities |
| `tlf-testing-kit` | Shared pytest fixtures, mock datasets, and statistical test helpers for cross-package validation. | — |

### Installation

```bash
pip install tlf-statistical-summary tlf-correlation-engine tlf-trend-detector
```

---

## npm Packages

| Package | Description |
|---------|-------------|
| `@tlf/analysis-sdk` | TypeScript client SDK for invoking all analysis APIs and retrieving results. |
| `@tlf/react-chart-components` | Reusable React components for rendering statistical charts, correlation heatmaps, and trend lines. |
| `@tlf/react-report-builder` | Drag-and-drop report builder UI for assembling stats, charts, and narrative into shareable reports. |
| `@tlf/anomaly-dashboard` | Real-time dashboard for reviewing flagged anomalies, scores, and drill-down details. |
| `@tlf/trend-visualizer` | Interactive time-series chart components with seasonal decomposition overlays. |
| `@tlf/comparison-ui` | Side-by-side dataset diff viewer for structural and value-level comparisons. |
| `@tlf/demographic-charts` | Specialized chart types for population pyramids, sector breakdowns, and regional maps. |
| `@tlf/indicator-monitor` | Widgets for tracking development indicators, threshold alerts, and historical timelines. |
| `@tlf/nlp-insight-ui` | Components for displaying extracted keywords, sentiment scores, and named entities from text datasets. |
| `@tlf/export-reports` | Client-side utilities for downloading analysis results and reports in PDF, HTML, or PNG formats. |

### Installation

```bash
npm install @tlf/analysis-sdk @tlf/react-chart-components
```

---

## Platform Services

The platform composes packages into deployable, scalable services:

| Service | Responsibility |
|---------|----------------|
| **Statistical Analysis Service** | Computes descriptive and inferential statistics, hypothesis tests, and regression models. |
| **Trend Detection Service** | Runs time-series decomposition, rolling averages, and cyclical pattern detection. |
| **Anomaly Detection Service** | Executes isolation forest and z-score pipelines; surfaces flagged records for review. |
| **Data Comparison Service** | Generates diff reports across dataset versions with structural and value-level detail. |
| **Correlation Analysis Service** | Calculates multi-variate correlation matrices and sector-relationship heatmaps. |
| **Demographic Profiling Service** | Produces population segmentations and policy-ready demographic profiles. |
| **Indicator Tracking Service** | Monitors development indicators over time and triggers threshold-based alerts. |
| **NLP Insight Extraction Service** | Processes regional-language text datasets through keyword, sentiment, and entity pipelines. |
| **Visualization Rendering Service** | Generates static and interactive charts, maps, and time-series plots on demand. |
| **Report Generation Service** | Assembles analysis outputs into HTML/PDF reports with narrative and visual components. |
| **Advanced Analytics Service** | Orchestrates ML/AI pipelines including regression, classification, and forecasting. |
| **Data Preprocessing Service** | Prepares raw datasets for analysis through normalization, encoding, and missing-value handling. |
| **Import/Export Service** | Async job queue for ingesting and exporting datasets in multiple formats. |
| **Integration Gateway Service** | API bridge and event bus for Data Manager, Data Explorer, and external BI tools. |
| **Audit & Logging Service** | Tracks analysis jobs, parameter changes, and result exports for compliance. |

---

## Development Roadmap

Based on the project issues, the implementation sequence is:

1. **Foundation — Data Handling & Statistics**
   - Implement basic data loading, structuring, and handling functions.
   - Build `tlf-statistical-summary` with descriptive stats calibrated for SGD/GCE sources.
   - Add `tlf-correlation-engine` for variable relationship analysis.

2. **Core Analysis — Hypothesis & Regression**
   - Implement statistical analysis functions including hypothesis testing.
   - Develop regression modules (linear, logistic, polynomial).

3. **Visualization — Charts & Demographics**
   - Implement data visualization functions with chart rendering.
   - Build `tlf-demographic-profiler` with visual breakdowns by region, age, and sector.
   - Add interactive time-series and plotly-based visualization modules.

4. **Advanced Techniques — Trends, NLP & Indicators**
   - Add support for advanced data analysis: time-series trend detection.
   - Implement `tlf-nlp-insight-extractor` for regional-language text datasets.
   - Build `tlf-indicator-tracker` for development indicator monitoring and alerting.

5. **Quality & Comparison — Cleaning & Diff**
   - Develop data preprocessing and cleaning functions (analysis-side).
   - Implement `tlf-anomaly-flagger` for outlier detection without disrupting data flow.
   - Build `tlf-data-comparator` for cross-dataset structural and value-level diffs.

6. **Interoperability — Import/Export & Toolkits**
   - Implement data import/export capabilities in CSV, JSON, Excel, and Parquet.
   - Assemble reusable data processing toolkit combining all foundational utilities.

7. **Platform Integration**
   - Expose all packages through unified API Gateway.
   - Build React-based UI packages for charting, reporting, and dashboarding.
   - Conduct integration testing with TLF Data Manager and TLF Data Explorer.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ or MongoDB 6+
- Redis 7+ (for caching and job queues)
- Optional: Elasticsearch 8+ (for indexing analysis results)

### Quick Start

```bash
# Clone the monorepo
git clone https://github.com/ctpl-git/TLF-Data-Analysis.git
cd TLF-Data-Analysis

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Node dependencies
npm install

# Run tests
pytest packages/tlf-statistical-summary/tests

# Start the platform
docker-compose up
```

The API will be available at `http://localhost:8000` and the analysis UI at `http://localhost:3000`.

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code style and linting (Black, Ruff, ESLint)
- Writing statistical and NLP tests
- Submitting pull requests
- Reporting data-quality issues

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by the TLF Team
</p>
