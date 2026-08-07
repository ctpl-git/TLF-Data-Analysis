"""
outlier.py — OutlierDetector
Flags subregions that are statistical outliers on any metric using
the IQR method. Works for any country's admin hierarchy (canonical
region/subregion columns).
"""

import pandas as pd


class OutlierDetector:
    """
    Detects outlier subregions using the IQR (Interquartile Range) method.
    A value is an outlier if it falls below Q1 - 1.5*IQR or above Q3 + 1.5*IQR.

    Usage:
        detector = OutlierDetector(df)
        outliers = detector.detect("total_population")
        print(detector.summary())
    """

    DETECTABLE_COLUMNS = [
        "total_population", "male", "female", "third_gender",
        "households", "urban_population", "rural_population",
        "literacy_rate", "avg_household_size",
    ]

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _validate_column(self, col: str):
        if col not in self.DETECTABLE_COLUMNS:
            raise ValueError(f"Column '{col}' not detectable. Choose from: {self.DETECTABLE_COLUMNS}")
        if col not in self.df.columns:
            raise ValueError(
                f"'{col}' is a valid metric but isn't present in this dataset "
                f"(this country's data may not publish it)."
            )

    def _iqr_bounds(self, col: str) -> tuple:
        Q1 = self.df[col].quantile(0.25)
        Q3 = self.df[col].quantile(0.75)
        IQR = Q3 - Q1
        return Q1 - 1.5 * IQR, Q3 + 1.5 * IQR

    def detect(self, col: str) -> pd.DataFrame:
        """
        Returns subregions that are outliers for a given metric.
        Includes whether they are 'high' or 'low' outliers.
        """
        self._validate_column(col)

        lower, upper = self._iqr_bounds(col)
        outliers = self.df[
            (self.df[col] < lower) | (self.df[col] > upper)
        ][["region", "subregion", col]].copy()

        outliers["outlier_type"] = outliers[col].apply(
            lambda v: "high" if v > upper else "low"
        )
        outliers["lower_bound"] = round(lower, 2)
        outliers["upper_bound"] = round(upper, 2)
        return outliers.sort_values(col, ascending=False).reset_index(drop=True)

    def summary(self) -> pd.DataFrame:
        """
        Runs outlier detection across all columns and returns
        a summary of how many outlier subregions exist per metric.
        """
        rows = []
        available_cols = [c for c in self.DETECTABLE_COLUMNS if c in self.df.columns]
        for col in available_cols:
            lower, upper = self._iqr_bounds(col)
            result = self.detect(col)
            rows.append({
                "metric": col,
                "outlier_count": len(result),
                "high_outliers": len(result[result["outlier_type"] == "high"]),
                "low_outliers": len(result[result["outlier_type"] == "low"]),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
            })
        return pd.DataFrame(rows)
