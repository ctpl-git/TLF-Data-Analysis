"""
rank.py — Ranker
Top-N / bottom-N / full ranking of rows by any numeric column the
caller names — no assumption about which column that should be
(no "subregion", no fixed metric list).
"""

import pandas as pd


class Ranker:
    """
    Usage:
        ranker = Ranker(df)
        ranker.top(5, by="rainfall_mm")
        ranker.bottom(5, by="rainfall_mm")
        ranker.rank(by="rainfall_mm")  # full ranking, descending
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _check_column(self, by: str):
        if by not in self.df.columns:
            raise ValueError(f"Column '{by}' not found in the data.")
        if not pd.api.types.is_numeric_dtype(self.df[by]):
            raise ValueError(f"Column '{by}' is not numeric, can't rank by it.")

    def top(self, n: int, by: str, label_column: str = None) -> pd.DataFrame:
        self._check_column(by)
        cols = [label_column, by] if label_column else self.df.columns.tolist()
        return self.df.nlargest(n, by)[cols] if label_column else self.df.nlargest(n, by)

    def bottom(self, n: int, by: str, label_column: str = None) -> pd.DataFrame:
        self._check_column(by)
        cols = [label_column, by] if label_column else self.df.columns.tolist()
        return self.df.nsmallest(n, by)[cols] if label_column else self.df.nsmallest(n, by)

    def rank(self, by: str, ascending: bool = False) -> pd.DataFrame:
        self._check_column(by)
        return self.df.sort_values(by=by, ascending=ascending)
