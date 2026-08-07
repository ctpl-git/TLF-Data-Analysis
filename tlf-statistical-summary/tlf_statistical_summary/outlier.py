"""
outlier.py — OutlierDetector
Flags outlier rows via the IQR method on any numeric column the caller
names. Same method as tlf-census-stats' OutlierDetector, just no
assumption about which metrics exist to check.
"""

import pandas as pd


class OutlierDetector:
    """
    Usage:
        detector = OutlierDetector(df)
        outliers = detector.detect(by="rainfall_mm")
    """

    def __init__(self, df: pd.DataFrame, multiplier: float = 1.5):
        self.df = df
        self.multiplier = multiplier

    def detect(self, by: str, label_column: str = None) -> pd.DataFrame:
        if by not in self.df.columns:
            raise ValueError(f"Column '{by}' not found in the data.")
        if not pd.api.types.is_numeric_dtype(self.df[by]):
            raise ValueError(f"Column '{by}' is not numeric, can't detect outliers on it.")

        series = self.df[by].dropna()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - self.multiplier * iqr
        upper = q3 + self.multiplier * iqr

        mask = (self.df[by] < lower) | (self.df[by] > upper)
        cols = [label_column, by] if label_column else self.df.columns.tolist()
        result = self.df[mask]
        return result[cols] if label_column else result
