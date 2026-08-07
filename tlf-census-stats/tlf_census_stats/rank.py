"""
rank.py — SubregionRanker
Ranks subregions by any numeric metric (population, literacy, etc.),
for any country's admin hierarchy (canonical region/subregion columns).
"""

import pandas as pd


class SubregionRanker:
    """
    Ranks all subregions by a chosen metric.

    Usage:
        ranker = SubregionRanker(df)
        print(ranker.top(10, by="literacy_rate"))
        print(ranker.bottom(5, by="total_population"))
    """

    RANKABLE_COLUMNS = [
        "total_population", "male", "female", "third_gender",
        "households", "urban_population", "rural_population",
        "literacy_rate", "avg_household_size",
    ]

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _validate_column(self, col: str):
        if col not in self.RANKABLE_COLUMNS:
            raise ValueError(
                f"Cannot rank by '{col}'. Choose from: {self.RANKABLE_COLUMNS}"
            )
        if col not in self.df.columns:
            raise ValueError(
                f"'{col}' is a valid metric but isn't present in this dataset "
                f"(this country's data may not publish it)."
            )

    def top(self, n: int = 10, by: str = "total_population") -> pd.DataFrame:
        """Top N subregions by metric."""
        self._validate_column(by)
        return (
            self.df[["region", "subregion", by]]
            .sort_values(by, ascending=False)
            .head(n)
            .reset_index(drop=True)
        )

    def bottom(self, n: int = 10, by: str = "total_population") -> pd.DataFrame:
        """Bottom N subregions by metric."""
        self._validate_column(by)
        return (
            self.df[["region", "subregion", by]]
            .sort_values(by, ascending=True)
            .head(n)
            .reset_index(drop=True)
        )

    def full_ranking(self, by: str = "total_population") -> pd.DataFrame:
        """All subregions ranked from highest to lowest."""
        self._validate_column(by)
        ranked = (
            self.df[["region", "subregion", by]]
            .sort_values(by, ascending=False)
            .reset_index(drop=True)
        )
        ranked.index += 1  # rank starts at 1
        ranked.index.name = "rank"
        return ranked

    def compare_subregions(self, subregions: list, by: str = "total_population") -> pd.DataFrame:
        """Compare specific subregions side by side."""
        self._validate_column(by)
        filtered = self.df[self.df["subregion"].isin(subregions)][
            ["region", "subregion", by]
        ].sort_values(by, ascending=False)
        return filtered.reset_index(drop=True)

    # Backward-compatible alias for the pre-refactor method name.
    def compare_districts(self, districts: list, by: str = "total_population") -> pd.DataFrame:
        return self.compare_subregions(districts, by=by)


# Backward-compatible alias for the pre-refactor class name.
DistrictRanker = SubregionRanker
