"""
profiler.py — ColumnProfiler
Inspects a DataFrame column-by-column and classifies each one as
numeric, datetime, or categorical/text, with no assumptions about what
any column is named or means. This replaces the fixed
region/subregion/total_population schema from tlf-census-stats: instead
of validating against a known set of expected columns, this just
reports what's actually in the file so the rest of the package (and any
interactive prompts) can work with whatever's there.
"""

from dataclasses import dataclass, field
from typing import List

import pandas as pd


@dataclass
class ColumnProfile:
    name: str
    dtype: str  # "numeric", "datetime", or "categorical"
    missing_count: int
    total_count: int
    unique_count: int


@dataclass
class DatasetProfile:
    columns: List[ColumnProfile] = field(default_factory=list)

    @property
    def numeric_columns(self) -> List[str]:
        return [c.name for c in self.columns if c.dtype == "numeric"]

    @property
    def categorical_columns(self) -> List[str]:
        return [c.name for c in self.columns if c.dtype == "categorical"]

    @property
    def datetime_columns(self) -> List[str]:
        return [c.name for c in self.columns if c.dtype == "datetime"]

    def print_summary(self):
        """Short, fixed-size overview regardless of column count — the
        default terminal output. Detailed per-column stats are opt-in
        (see print_column_list) or live in the auto-written report file."""
        total = len(self.columns)
        print(
            f"[ColumnProfiler] {total} column(s) detected: "
            f"{len(self.numeric_columns)} numeric, "
            f"{len(self.categorical_columns)} categorical, "
            f"{len(self.datetime_columns)} datetime."
        )

    def print_column_list(self, names: List[str] = None):
        """Detailed one-line-per-column listing (type/unique/missing).
        Restrict to `names` to avoid dumping hundreds of lines at once."""
        columns = [c for c in self.columns if names is None or c.name in names]
        print("[ColumnProfiler] Columns:")
        for c in columns:
            pct_missing = (c.missing_count / c.total_count * 100) if c.total_count else 0
            print(
                f"    {c.name!r}: {c.dtype} "
                f"({c.unique_count} unique, {c.missing_count} missing / {pct_missing:.0f}%)"
            )


class ColumnProfiler:
    """
    Classifies every column in a DataFrame as numeric, datetime, or
    categorical — coercing numeric-looking strings (e.g. "1,234" from a
    messy CSV/Excel export) to actual numbers first, and attempting a
    datetime parse before falling back to categorical/text.

    Usage:
        profiler = ColumnProfiler(df)
        profile = profiler.profile()
        profile.print_report()
        profile.numeric_columns   # e.g. ["temperature_c", "rainfall_mm"]
    """

    # A column with more unique values than this fraction of its row
    # count is treated as free text rather than a meaningful category
    # (mainly relevant for open-ended text fields, not used to block
    # anything — just informational for now).
    FREE_TEXT_UNIQUE_RATIO = 0.9

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def profile(self) -> DatasetProfile:
        result = DatasetProfile()
        for col in self.df.columns:
            series = self.df[col]
            dtype, coerced = self._classify(series)
            self.df[col] = coerced
            result.columns.append(
                ColumnProfile(
                    name=col,
                    dtype=dtype,
                    missing_count=int(coerced.isna().sum()),
                    total_count=len(coerced),
                    unique_count=int(coerced.nunique(dropna=True)),
                )
            )
        return result

    def _classify(self, series: pd.Series):
        # Already numeric.
        if pd.api.types.is_numeric_dtype(series):
            return "numeric", series

        # Already datetime.
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime", series

        # Try coercing text to numeric (handles "1,234", " 56 ", etc.).
        cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
        as_numeric = pd.to_numeric(cleaned, errors="coerce")
        # Only accept the numeric coercion if it didn't just turn
        # everything into NaN (i.e. the column really was numeric-ish).
        non_null_original = series.notna().sum()
        if non_null_original > 0 and as_numeric.notna().sum() / non_null_original >= 0.9:
            return "numeric", as_numeric

        # Try coercing to datetime, same acceptance threshold.
        as_datetime = pd.to_datetime(series, errors="coerce", format="mixed")
        if non_null_original > 0 and as_datetime.notna().sum() / non_null_original >= 0.9:
            return "datetime", as_datetime

        # Otherwise: categorical/text, unchanged.
        return "categorical", series
