"""
tests/test_tlf_census_stats.py
Unit tests for the tlf_census_stats package.
Run with: python -m pytest packages/tlf_census_stats/tests/ -v
"""

import sys
import os
import pytest
import pandas as pd

from tlf_census_stats.loader import CensusLoader
from tlf_census_stats.describe import DataDescriber
from tlf_census_stats.aggregate import RegionAggregator
from tlf_census_stats.rank import SubregionRanker
from tlf_census_stats.outlier import OutlierDetector
from tlf_census_stats.report import StatsReporter
from tlf_census_stats.country_profiles import get_profile, COUNTRY_PROFILES

# These fixtures live in tests/fixtures/, owned by the test suite itself —
# deliberately NOT the same files bundled into the package for end users
# (see tlf_census_stats/data/sample/). Decoupling the two means changing
# what ships as a demo/quickstart sample can't silently break tests, and
# vice versa: test fixtures can grow more edge cases over time without
# bloating what actually gets installed via pip.
_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
NEPAL_DATA_PATH = os.path.join(_FIXTURES_DIR, "nepal_census_2021.csv")
BANGLADESH_DATA_PATH = os.path.join(_FIXTURES_DIR, "bangladesh_census_2022.csv")


@pytest.fixture
def df():
    loader = CensusLoader(NEPAL_DATA_PATH, country="nepal")
    return loader.load()


@pytest.fixture
def bd_df():
    loader = CensusLoader(BANGLADESH_DATA_PATH, country="bangladesh")
    return loader.load()


# --- CountryProfile ---
class TestCountryProfiles:
    def test_all_profiles_have_labels(self):
        for code, profile in COUNTRY_PROFILES.items():
            assert profile.region_label
            assert profile.subregion_label
            assert "region" in profile.required_columns
            assert "subregion" in profile.required_columns

    def test_unknown_country_raises(self):
        with pytest.raises(ValueError):
            get_profile("atlantis")

    def test_lookup_is_case_insensitive(self):
        assert get_profile("NEPAL").code == "nepal"
        assert get_profile("Sri Lanka").code == "sri_lanka"


# --- CensusLoader ---
class TestCensusLoader:
    def test_loads_successfully(self, df):
        assert df is not None
        assert len(df) > 0

    def test_required_columns_present(self, df):
        for col in ["region", "subregion", "total_population", "literacy_rate"]:
            assert col in df.columns

    def test_no_negative_population(self, df):
        assert (df["total_population"] >= 0).all()

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            CensusLoader("nonexistent.csv", country="nepal").load()

    def test_unknown_country_raises(self):
        with pytest.raises(ValueError):
            CensusLoader(NEPAL_DATA_PATH, country="atlantis")

    def test_loads_second_country(self, bd_df):
        """Same loader/schema works for a different country's raw column names."""
        assert bd_df is not None
        assert len(bd_df) > 0
        assert "region" in bd_df.columns
        assert "subregion" in bd_df.columns


# --- DataDescriber ---
class TestDataDescriber:
    def test_summary_shape(self, df):
        describer = DataDescriber(df)
        summary = describer.summary()
        assert "mean" in summary.columns
        assert "median" in summary.columns
        assert len(summary) == len(DataDescriber.NUMERIC_COLS)

    def test_gender_ratio_positive(self, df):
        describer = DataDescriber(df)
        ratios = describer.gender_ratio()
        assert (ratios > 0).all()

    def test_urbanization_between_0_100(self, df):
        describer = DataDescriber(df)
        rates = describer.urbanization_rate()
        assert (rates >= 0).all()
        assert (rates <= 100).all()

    def test_national_totals_keys(self, df):
        describer = DataDescriber(df)
        totals = describer.national_totals()
        assert "total_population" in totals
        assert "national_literacy_rate" in totals
        assert totals["total_population"] > 0

    def test_national_totals_on_second_country(self, bd_df):
        describer = DataDescriber(bd_df)
        totals = describer.national_totals()
        assert totals["total_regions"] == bd_df["region"].nunique()


# --- RegionAggregator ---
class TestRegionAggregator:
    def test_region_count(self, df):
        agg = RegionAggregator(df)
        result = agg.aggregate()
        assert len(result) == df["region"].nunique()

    def test_population_share_sums_to_100(self, df):
        agg = RegionAggregator(df)
        share = agg.region_share()
        total = share["population_share_pct"].sum()
        assert abs(total - 100.0) < 0.1

    def test_most_populous_is_string(self, df):
        agg = RegionAggregator(df)
        assert isinstance(agg.most_populous_region(), str)

    def test_works_on_second_country(self, bd_df):
        agg = RegionAggregator(bd_df)
        result = agg.aggregate()
        assert len(result) == bd_df["region"].nunique()
        assert "Dhaka" in result["region"].values


# --- SubregionRanker ---
class TestSubregionRanker:
    def test_top_n_length(self, df):
        ranker = SubregionRanker(df)
        result = ranker.top(5, by="total_population")
        assert len(result) == 5

    def test_bottom_n_ascending(self, df):
        ranker = SubregionRanker(df)
        result = ranker.bottom(5, by="literacy_rate")
        assert result["literacy_rate"].is_monotonic_increasing

    def test_invalid_column_raises(self, df):
        ranker = SubregionRanker(df)
        with pytest.raises(ValueError):
            ranker.top(5, by="nonexistent_col")

    def test_compare_subregions(self, df):
        ranker = SubregionRanker(df)
        result = ranker.compare_subregions(["Kathmandu", "Humla"], by="literacy_rate")
        assert len(result) == 2


# --- Alias detection + optional numeric columns ---
class TestAliasAndOptionalColumns:
    def _write_minimal_india_csv(self, tmp_path):
        """
        Deliberately: (a) uses alias header names instead of exact
        canonical ones, and (b) omits every optional numeric column
        (no urban/rural population, no literacy rate, no household size).
        """
        path = tmp_path / "india_minimal.csv"
        path.write_text(
            "State,District,Population,Male Population,Female Population,Number of households\n"
            "Punjab,Amritsar,2490656,1310075,1180581,441586\n"
            "Punjab,Ludhiana,3498739,1858602,1640137,689253\n"
            "Kerala,Kochi,2117990,1027564,1090426,547471\n"
        )
        return str(path)

    def test_loads_with_alias_headers_and_missing_optional_columns(self, tmp_path):
        csv_path = self._write_minimal_india_csv(tmp_path)
        loader = CensusLoader(csv_path, country="india")
        df = loader.load()

        assert "region" in df.columns
        assert "subregion" in df.columns
        assert "total_population" in df.columns
        assert "male" in df.columns
        assert "female" in df.columns
        assert "households" in df.columns
        # Optional fields genuinely absent from the source file stay absent.
        assert "literacy_rate" not in df.columns
        assert "avg_household_size" not in df.columns
        assert df["total_population"].iloc[0] == 2490656

    def test_validation_report_flags_missing_optional_as_warning_not_error(self, tmp_path):
        csv_path = self._write_minimal_india_csv(tmp_path)
        loader = CensusLoader(csv_path, country="india")
        loader.load()
        report = {row["column"]: row for row in loader.validation_report}
        assert report["literacy_rate"]["present"] is False
        assert report["literacy_rate"]["required"] is False

    def test_full_report_runs_without_optional_columns(self, tmp_path):
        """The whole StatsReporter pipeline should complete, not crash, on minimal data."""
        csv_path = self._write_minimal_india_csv(tmp_path)
        reporter = StatsReporter(csv_path, country="india")
        reporter.run()  # should not raise
        region_summary = reporter.get("region_summary")
        assert "avg_literacy_rate" not in region_summary.columns
        assert reporter.get("top5_literacy") is None  # skipped, never populated

    def test_missing_required_column_still_raises(self, tmp_path):
        path = tmp_path / "india_broken.csv"
        path.write_text("State,District,Population\nPunjab,Amritsar,2490656\n")
        loader = CensusLoader(str(path), country="india")
        with pytest.raises(ValueError):
            loader.load()

    def test_row_with_missing_population_is_dropped_not_fatal(self, tmp_path, capsys):
        """A single incomplete row (e.g. a district whose Total/Rural rows
        got lost during PDF extraction) should be dropped with a warning,
        not abort the load for every other good row."""
        path = tmp_path / "india_one_bad_row.csv"
        path.write_text(
            "State,District,Population,Male Population,Female Population,Number of households\n"
            "Punjab,Amritsar,2490656,1310075,1180581,441586\n"
            "Gujarat,Kachchh,,,,\n"  # blank -> NaN, mirrors the real Kachchh row
            "Kerala,Kochi,2117990,1027564,1090426,547471\n"
        )
        loader = CensusLoader(str(path), country="india")
        df = loader.load()  # must not raise
        assert len(df) == 2
        assert "Kachchh" not in set(df["subregion"])
        assert "dropping 1" in capsys.readouterr().out

    def test_row_with_negative_population_is_dropped_not_fatal(self, tmp_path, capsys):
        path = tmp_path / "india_negative_row.csv"
        path.write_text(
            "State,District,Population,Male Population,Female Population,Number of households\n"
            "Punjab,Amritsar,2490656,1310075,1180581,441586\n"
            "Gujarat,BadRow,-100,-50,-50,10\n"
            "Kerala,Kochi,2117990,1027564,1090426,547471\n"
        )
        loader = CensusLoader(str(path), country="india")
        df = loader.load()  # must not raise
        assert len(df) == 2
        assert "BadRow" not in set(df["subregion"])
        assert "dropping 1" in capsys.readouterr().out

    def test_full_report_runs_when_some_rows_are_dropped(self, tmp_path):
        """The whole StatsReporter pipeline should complete on the remaining
        good rows even when one row had to be dropped."""
        path = tmp_path / "india_one_bad_row_report.csv"
        path.write_text(
            "State,District,Population,Male Population,Female Population,Number of households\n"
            "Punjab,Amritsar,2490656,1310075,1180581,441586\n"
            "Gujarat,Kachchh,,,,\n"
            "Kerala,Kochi,2117990,1027564,1090426,547471\n"
        )
        reporter = StatsReporter(str(path), country="india")
        reporter.run()  # should not raise
        assert len(reporter.get("region_summary")) == 2


# --- OutlierDetector ---
class TestOutlierDetector:
    def test_detect_returns_dataframe(self, df):
        detector = OutlierDetector(df)
        result = detector.detect("total_population")
        assert isinstance(result, pd.DataFrame)

    def test_outlier_type_values(self, df):
        detector = OutlierDetector(df)
        result = detector.detect("total_population")
        if len(result) > 0:
            assert set(result["outlier_type"]).issubset({"high", "low"})

    def test_summary_covers_all_columns(self, df):
        detector = OutlierDetector(df)
        summary = detector.summary()
        assert len(summary) == len(OutlierDetector.DETECTABLE_COLUMNS)
