"""
tests/test_tlf_statistical_summary.py
Unit tests for the tlf_statistical_summary package.
Run with: python -m pytest packages/tlf_statistical_summary/tests/ -v
"""

import json
import os
import subprocess
import sys

import pandas as pd
import pytest


from tlf_statistical_summary.loader import TabularLoader, UnsupportedFileError
from tlf_statistical_summary.profiler import ColumnProfiler
from tlf_statistical_summary.describe import Describer
from tlf_statistical_summary.rank import Ranker
from tlf_statistical_summary.outlier import OutlierDetector
from tlf_statistical_summary.aggregate import Aggregator
from tlf_statistical_summary.report import Reporter
from tlf_statistical_summary.errors import ReportWriteError


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

WEATHER_ROWS = [
    {"station": "Kathmandu", "date": "2026-01-01", "temp_c": 12.5, "rainfall_mm": 0.0, "humidity_pct": 55},
    {"station": "Kathmandu", "date": "2026-01-02", "temp_c": 13.1, "rainfall_mm": 2.4, "humidity_pct": 60},
    {"station": "Pokhara", "date": "2026-01-01", "temp_c": 15.2, "rainfall_mm": 12.0, "humidity_pct": 70},
    {"station": "Pokhara", "date": "2026-01-02", "temp_c": 14.8, "rainfall_mm": 150.0, "humidity_pct": 75},
]


@pytest.fixture
def weather_csv(tmp_path):
    path = tmp_path / "weather.csv"
    pd.DataFrame(WEATHER_ROWS).to_csv(path, index=False)
    return str(path)


@pytest.fixture
def weather_df():
    return pd.DataFrame(WEATHER_ROWS)


@pytest.fixture
def loaded_profile(weather_df):
    """A (df, profile) pair with column types already classified, matching
    the shape Describer/Reporter expect."""
    df = weather_df.copy()
    profile = ColumnProfiler(df).profile()
    return df, profile


# ---------------------------------------------------------------------------
# loader.py — TabularLoader
# ---------------------------------------------------------------------------

class TestTabularLoader:
    def test_reads_csv(self, weather_csv):
        df = TabularLoader(weather_csv).load()
        assert len(df) == 4
        assert list(df.columns) == ["station", "date", "temp_c", "rainfall_mm", "humidity_pct"]

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TabularLoader(str(tmp_path / "nope.csv")).load()

    def test_pdf_raises_unsupported_with_guidance(self, tmp_path):
        path = tmp_path / "report.pdf"
        path.touch()
        with pytest.raises(UnsupportedFileError, match="tlf-data-cleaning"):
            TabularLoader(str(path)).load()

    def test_unknown_extension_raises_unsupported(self, tmp_path):
        path = tmp_path / "data.txt"
        path.touch()
        with pytest.raises(UnsupportedFileError):
            TabularLoader(str(path)).load()

    def test_reads_json_list_of_records(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text(json.dumps(WEATHER_ROWS))
        df = TabularLoader(str(path)).load()
        assert len(df) == 4

    def test_reads_json_single_object_as_one_row(self, tmp_path):
        path = tmp_path / "meta.json"
        path.write_text(json.dumps({"name": "a dataset", "size": 123}))
        df = TabularLoader(str(path)).load()
        assert len(df) == 1
        assert list(df.columns) == ["name", "size"]

    def test_json_wrong_shape_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([1, 2, 3]))  # list of scalars, not records
        # pandas will actually construct a DataFrame from a list of ints, so
        # this only raises for shapes pandas itself can't turn into rows —
        # confirm the wrong-shape branch specifically with a nested dict of dicts.
        path.write_text(json.dumps("just a string"))
        with pytest.raises(UnsupportedFileError):
            TabularLoader(str(path)).load()

    def test_reads_single_excel_sheet_by_default(self, tmp_path):
        path = tmp_path / "one_sheet.xlsx"
        pd.DataFrame(WEATHER_ROWS).to_excel(path, index=False)
        df = TabularLoader(str(path)).load()
        assert len(df) == 4

    def test_excel_multi_sheet_stacks_by_default(self, tmp_path):
        path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"District": ["A"], "Value": [1]}).to_excel(writer, sheet_name="S1", index=False)
            pd.DataFrame({"District": ["B"], "Value": [2]}).to_excel(writer, sheet_name="S2", index=False)
        df = TabularLoader(str(path)).load()
        assert len(df) == 2  # stacked rows, one per sheet
        assert set(df["District"]) == {"A", "B"}

    def test_excel_single_sheet_selection(self, tmp_path):
        path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"District": ["A"], "Value": [1]}).to_excel(writer, sheet_name="S1", index=False)
            pd.DataFrame({"District": ["B"], "Extra": [2]}).to_excel(writer, sheet_name="S2", index=False)
        df = TabularLoader(str(path), sheet=["S1"]).load()
        assert len(df) == 1
        assert "Extra" not in df.columns

    def test_excel_merge_on_combines_side_by_side(self, tmp_path):
        path = tmp_path / "merge.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"District": ["A", "B"], "Population": [100, 200]}).to_excel(
                writer, sheet_name="Pop", index=False)
            pd.DataFrame({"District": ["A", "B"], "Literacy": [55.0, 60.0]}).to_excel(
                writer, sheet_name="Lit", index=False)
        df = TabularLoader(str(path), merge_on="District").load()
        assert len(df) == 2  # one row per district, not stacked
        assert set(df.columns) >= {"District", "Pop_Population", "Lit_Literacy"}

    def test_excel_merge_on_missing_key_raises(self, tmp_path):
        path = tmp_path / "merge.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"NoKeyHere": [1]}).to_excel(writer, sheet_name="S1", index=False)
        with pytest.raises(ValueError, match="merge on"):
            TabularLoader(str(path), merge_on="District").load()

    def test_list_sheets_returns_names_for_excel(self, tmp_path):
        path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="First", index=False)
            pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Second", index=False)
        assert TabularLoader(str(path)).list_sheets() == ["First", "Second"]

    def test_list_sheets_empty_for_csv(self, weather_csv):
        assert TabularLoader(weather_csv).list_sheets() == []


# ---------------------------------------------------------------------------
# profiler.py — ColumnProfiler
# ---------------------------------------------------------------------------

class TestColumnProfiler:
    def test_classifies_numeric_categorical_datetime(self, weather_df):
        profile = ColumnProfiler(weather_df).profile()
        assert "temp_c" in profile.numeric_columns
        assert "rainfall_mm" in profile.numeric_columns
        assert "station" in profile.categorical_columns
        assert "date" in profile.datetime_columns

    def test_coerces_messy_numeric_strings(self):
        df = pd.DataFrame({"amount": ["1,234", "5,678", "9,012"]})
        profile = ColumnProfiler(df).profile()
        assert "amount" in profile.numeric_columns

    def test_missing_value_counts(self):
        df = pd.DataFrame({"x": [1, 2, None, 4]})
        profile = ColumnProfiler(df).profile()
        col = next(c for c in profile.columns if c.name == "x")
        assert col.missing_count == 1
        assert col.total_count == 4

    def test_mostly_text_stays_categorical(self):
        df = pd.DataFrame({"notes": ["alpha", "beta", "gamma completely different"]})
        profile = ColumnProfiler(df).profile()
        assert "notes" in profile.categorical_columns

    def test_print_summary_and_column_list_do_not_raise(self, weather_df, capsys):
        profile = ColumnProfiler(weather_df).profile()
        profile.print_summary()
        profile.print_column_list()
        profile.print_column_list(names=["temp_c"])
        out = capsys.readouterr().out
        assert "column(s) detected" in out


# ---------------------------------------------------------------------------
# describe.py — Describer
# ---------------------------------------------------------------------------

class TestDescriber:
    def test_numeric_stats(self, loaded_profile):
        df, profile = loaded_profile
        stats = Describer(df, profile).describe()
        s = stats["rainfall_mm"]
        assert s["count"] == 4
        assert s["min"] == 0.0
        assert s["max"] == 150.0

    def test_categorical_stats(self, loaded_profile):
        df, profile = loaded_profile
        stats = Describer(df, profile).describe()
        s = stats["station"]
        assert s["unique"] == 2
        assert s["most_common"] in ("Kathmandu", "Pokhara")

    def test_datetime_stats(self, loaded_profile):
        df, profile = loaded_profile
        stats = Describer(df, profile).describe()
        s = stats["date"]
        assert s["span_days"] == 1

    def test_empty_column_returns_count_zero(self):
        df = pd.DataFrame({"x": [None, None]})
        profile = ColumnProfiler(df).profile()
        stats = Describer(df, profile).describe()
        assert stats["x"]["count"] == 0

    def test_write_full_report_contains_every_column(self, loaded_profile, tmp_path):
        df, profile = loaded_profile
        path = tmp_path / "full_report.txt"
        Describer(df, profile).write_full_report(str(path))
        content = path.read_text()
        for col in df.columns:
            assert col in content

    def test_print_report_restricts_to_requested_columns(self, loaded_profile, capsys):
        df, profile = loaded_profile
        Describer(df, profile).print_report(columns=["rainfall_mm"])
        out = capsys.readouterr().out
        assert "rainfall_mm" in out
        assert "humidity_pct" not in out


# ---------------------------------------------------------------------------
# rank.py — Ranker
# ---------------------------------------------------------------------------

class TestRanker:
    def test_top_n(self, weather_df):
        top = Ranker(weather_df).top(2, by="rainfall_mm")
        assert list(top["rainfall_mm"]) == [150.0, 12.0]

    def test_bottom_n(self, weather_df):
        bottom = Ranker(weather_df).bottom(2, by="rainfall_mm")
        assert list(bottom["rainfall_mm"]) == [0.0, 2.4]

    def test_label_column_restricts_output_columns(self, weather_df):
        top = Ranker(weather_df).top(1, by="rainfall_mm", label_column="station")
        assert list(top.columns) == ["station", "rainfall_mm"]

    def test_unknown_column_raises(self, weather_df):
        with pytest.raises(ValueError, match="not found"):
            Ranker(weather_df).top(1, by="nope")

    def test_non_numeric_column_raises(self, weather_df):
        with pytest.raises(ValueError, match="not numeric"):
            Ranker(weather_df).top(1, by="station")

    def test_full_rank_sorted_descending_by_default(self, weather_df):
        ranked = Ranker(weather_df).rank(by="temp_c")
        assert list(ranked["temp_c"]) == sorted(weather_df["temp_c"], reverse=True)


# ---------------------------------------------------------------------------
# outlier.py — OutlierDetector
# ---------------------------------------------------------------------------

class TestOutlierDetector:
    def test_detects_high_outlier(self):
        # 20 normal points + one clear outlier, enough for IQR to be meaningful.
        df = pd.DataFrame({"value": [10, 11, 9, 10, 12, 11, 10, 9, 10, 11] * 2 + [500]})
        outliers = OutlierDetector(df).detect(by="value")
        assert 500 in outliers["value"].values

    def test_no_outliers_on_uniform_data(self):
        df = pd.DataFrame({"value": [10, 10, 10, 10, 10]})
        outliers = OutlierDetector(df).detect(by="value")
        assert outliers.empty

    def test_label_column_restricts_output(self):
        df = pd.DataFrame({
            "name": [f"n{i}" for i in range(20)] + ["outlier_row"],
            "value": [10, 11, 9, 10, 12, 11, 10, 9, 10, 11] * 2 + [500],
        })
        outliers = OutlierDetector(df).detect(by="value", label_column="name")
        assert list(outliers.columns) == ["name", "value"]

    def test_unknown_column_raises(self, weather_df):
        with pytest.raises(ValueError, match="not found"):
            OutlierDetector(weather_df).detect(by="nope")

    def test_non_numeric_column_raises(self, weather_df):
        with pytest.raises(ValueError, match="not numeric"):
            OutlierDetector(weather_df).detect(by="station")


# ---------------------------------------------------------------------------
# aggregate.py — Aggregator
# ---------------------------------------------------------------------------

class TestAggregator:
    def test_group_by_sum(self, weather_df):
        result = Aggregator(weather_df).group_by("station", agg="sum")
        row = result[result["station"] == "Pokhara"].iloc[0]
        assert row["rainfall_mm"] == 162.0

    def test_group_by_mean(self, weather_df):
        result = Aggregator(weather_df).group_by("station", agg="mean")
        row = result[result["station"] == "Kathmandu"].iloc[0]
        assert row["rainfall_mm"] == pytest.approx(1.2)

    def test_unknown_column_raises(self, weather_df):
        with pytest.raises(ValueError, match="not found"):
            Aggregator(weather_df).group_by("nope")

    def test_bad_agg_raises(self, weather_df):
        with pytest.raises(ValueError, match="Unsupported aggregation"):
            Aggregator(weather_df).group_by("station", agg="median")

    def test_no_numeric_columns_raises(self):
        df = pd.DataFrame({"group": ["a", "b"], "label": ["x", "y"]})
        with pytest.raises(ValueError, match="No numeric columns"):
            Aggregator(df).group_by("group")


# ---------------------------------------------------------------------------
# report.py — Reporter (integration)
# ---------------------------------------------------------------------------

class TestReporter:
    def test_full_run_populates_results(self, weather_csv):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe", "rank", "outliers"], group_by="station",
              metric_column="rainfall_mm", top_n=2)
        assert r._group_summary is not None
        assert r._rank_result is not None
        assert r._outlier_result is not None

    def test_run_writes_full_report_file(self, weather_csv, tmp_path):
        report_path = tmp_path / "custom_report.txt"
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe"], report_path=str(report_path))
        assert report_path.exists()
        assert "rainfall_mm" in report_path.read_text()

    def test_export_csv_contains_all_sections(self, weather_csv, tmp_path):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe", "rank", "outliers"], group_by="station", metric_column="rainfall_mm")
        out_path = tmp_path / "export.csv"
        r.export("csv", str(out_path))
        content = out_path.read_text()
        assert "Grouped summary" in content
        assert "Ranking" in content
        assert "Outliers" in content

    def test_export_json_contains_all_sections(self, weather_csv, tmp_path):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe", "rank", "outliers"], group_by="station", metric_column="rainfall_mm")
        out_path = tmp_path / "export.json"
        r.export("json", str(out_path))
        payload = json.loads(out_path.read_text())
        assert "grouped_summary" in payload
        assert "ranking" in payload
        assert "outliers" in payload

    def test_export_falls_back_to_raw_data_without_stats(self, weather_csv, tmp_path):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe"])  # no group_by/rank/outliers
        out_path = tmp_path / "export.csv"
        r.export("csv", str(out_path))
        content = out_path.read_text()
        assert "Data" in content
        assert "station" in content

    def test_export_html_produces_self_contained_file(self, weather_csv, tmp_path):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe", "rank"], group_by="station", metric_column="rainfall_mm")
        out_path = tmp_path / "report.html"
        r.export("html", str(out_path))
        content = out_path.read_text()
        assert "<html>" in content
        assert "base64" in content

    def test_export_unsupported_format_raises(self, weather_csv, tmp_path):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe"])
        with pytest.raises(ValueError, match="Unsupported export format"):
            r.export("yaml", str(tmp_path / "x.yaml"))

    def test_export_locked_file_raises_clean_error(self, weather_csv, tmp_path, monkeypatch):
        r = Reporter(weather_csv)
        r.load()
        r.run(stats=["describe"], group_by="station")

        locked_path = tmp_path / "locked.csv"
        real_open = open

        def fake_open(path, mode="r", *a, **kw):
            if str(path) == str(locked_path) and "w" in mode:
                raise PermissionError(13, "Permission denied")
            return real_open(path, mode, *a, **kw)

        monkeypatch.setattr("builtins.open", fake_open)
        with pytest.raises(ReportWriteError, match="open in another program"):
            r.export("csv", str(locked_path))


# ---------------------------------------------------------------------------
# main.py — CLI smoke tests (--yes / non-interactive)
# ---------------------------------------------------------------------------

class TestCliSmoke:
    """These assume the package itself is installed (e.g. `pip install -e .`
    from tlf-statistical-summary/), so `-m tlf_statistical_summary.main`
    resolves from any working directory — no repo-relative path math needed."""

    def _run_cli(self, args):
        return subprocess.run(
            [sys.executable, "-m", "tlf_statistical_summary.main"] + args,
            capture_output=True, text=True, timeout=30,
        )

    def test_yes_mode_full_run_and_export(self, weather_csv, tmp_path):
        export_path = tmp_path / "cli_export.csv"
        result = self._run_cli([
            "--data", weather_csv, "--yes",
            "--group-by", "station", "--metric", "rainfall_mm",
            "--stats", "describe,rank,outliers",
            "--export", "csv", "--export-path", str(export_path),
        ])
        assert result.returncode == 0, result.stderr
        assert export_path.exists()
        assert "Grouped summary" in export_path.read_text()

    def test_yes_mode_missing_data_fails_loudly(self, tmp_path):
        result = self._run_cli(["--yes"])
        assert result.returncode != 0
        assert "--data" in (result.stdout + result.stderr)

    def test_yes_mode_missing_metric_for_rank_fails_loudly(self, weather_csv, tmp_path):
        result = self._run_cli(["--data", weather_csv, "--yes", "--stats", "rank"])
        assert result.returncode != 0
        assert "--metric" in (result.stdout + result.stderr)

    def test_yes_mode_skips_aggregation_without_group_by(self, weather_csv, tmp_path):
        result = self._run_cli(["--data", weather_csv, "--yes", "--stats", "describe"])
        assert result.returncode == 0, result.stderr
        assert "Aggregator" not in result.stdout
