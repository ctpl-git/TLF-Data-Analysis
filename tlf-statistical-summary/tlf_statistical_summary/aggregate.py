"""
aggregate.py — Aggregator
Groups rows by a column the caller names (no fixed "region"/"subregion"
hierarchy) and sums/averages every numeric column found. This is the
one place a schema-free design still needs a piece of information from
somewhere — there's no reliable way to auto-detect which column is
meant to be the grouping key, so it's always supplied explicitly,
either via a CLI flag or an interactive prompt (see interactive.py).
"""

import pandas as pd


class Aggregator:
    """
    Usage:
        aggregator = Aggregator(df)
        summary = aggregator.group_by("station", agg="sum")
        summary = aggregator.group_by("station", agg="mean")
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def group_by(self, column: str, agg: str = "sum") -> pd.DataFrame:
        if column not in self.df.columns:
            raise ValueError(f"Group-by column '{column}' not found in the data.")
        if agg not in ("sum", "mean"):
            raise ValueError(f"Unsupported aggregation '{agg}'; use 'sum' or 'mean'.")

        numeric_cols = self.df.select_dtypes(include="number").columns.tolist()
        if not numeric_cols:
            raise ValueError("No numeric columns found to aggregate.")

        grouped = self.df.groupby(column)[numeric_cols]
        result = grouped.sum() if agg == "sum" else grouped.mean()
        return result.reset_index()
