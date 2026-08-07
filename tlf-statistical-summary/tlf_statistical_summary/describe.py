"""
describe.py — Describer
Produces descriptive stats for every column in a DataFrame, branching
by column type (numeric vs categorical vs datetime) rather than
assuming any fixed set of fields. No domain-specific derived metrics
(no gender ratio, no urbanization rate, etc.) — those belong to a
domain-specific package (e.g. tlf-census-stats) built on top of this,
not to the generic core.
"""

import pandas as pd

from .profiler import DatasetProfile
from .errors import open_for_write


class Describer:
    """
    Usage:
        describer = Describer(df, profile)
        stats = describer.describe()   # dict keyed by column name
        describer.print_report()
    """

    def __init__(self, df: pd.DataFrame, profile: DatasetProfile):
        self.df = df
        self.profile = profile

    def describe(self) -> dict:
        stats = {}
        for col_profile in self.profile.columns:
            col = col_profile.name
            if col_profile.dtype == "numeric":
                stats[col] = self._describe_numeric(self.df[col])
            elif col_profile.dtype == "datetime":
                stats[col] = self._describe_datetime(self.df[col])
            else:
                stats[col] = self._describe_categorical(self.df[col])
        return stats

    def _describe_numeric(self, series: pd.Series) -> dict:
        clean = series.dropna()
        if clean.empty:
            return {"count": 0}
        return {
            "count": int(clean.count()),
            "mean": float(clean.mean()),
            "median": float(clean.median()),
            "std": float(clean.std()) if len(clean) > 1 else 0.0,
            "min": float(clean.min()),
            "max": float(clean.max()),
            "q1": float(clean.quantile(0.25)),
            "q3": float(clean.quantile(0.75)),
            "skew": float(clean.skew()) if len(clean) > 2 else 0.0,
        }

    def _describe_categorical(self, series: pd.Series) -> dict:
        clean = series.dropna()
        if clean.empty:
            return {"count": 0}
        value_counts = clean.value_counts()
        return {
            "count": int(clean.count()),
            "unique": int(clean.nunique()),
            "most_common": value_counts.index[0],
            "most_common_count": int(value_counts.iloc[0]),
            "least_common": value_counts.index[-1],
            "least_common_count": int(value_counts.iloc[-1]),
        }

    def _describe_datetime(self, series: pd.Series) -> dict:
        clean = series.dropna()
        if clean.empty:
            return {"count": 0}
        return {
            "count": int(clean.count()),
            "earliest": clean.min(),
            "latest": clean.max(),
            "span_days": (clean.max() - clean.min()).days,
        }

    def print_report(self, columns: list = None):
        """Prints full per-column stats. Restrict to `columns` for a
        subset — printing every column for a wide dataset is unreadable
        in a terminal (use write_full_report for the complete version)."""
        stats = self.describe()
        if columns is not None:
            stats = {k: v for k, v in stats.items() if k in columns}
        print("[Describer] Column statistics:")
        for col, s in stats.items():
            print(f"  {col!r}:")
            for k, v in s.items():
                print(f"      {k}: {v}")

    def write_full_report(self, path: str):
        """Writes full per-column stats for every column to a text file,
        regardless of how many columns there are — this is where the
        complete detail always lives, even when the terminal only shows
        a summary."""
        stats = self.describe()
        with open_for_write(path, "w", encoding="utf-8") as f:
            f.write(f"Full column statistics ({len(stats)} columns)\n")
            f.write("=" * 60 + "\n\n")
            for col, s in stats.items():
                f.write(f"{col}\n")
                for k, v in s.items():
                    f.write(f"    {k}: {v}\n")
                f.write("\n")
