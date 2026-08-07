"""
aggregate.py — RegionAggregator
Groups subregion-level data up to region level with key metrics.
Works for any country's admin hierarchy via canonical region/subregion
columns (see country_profiles.py). Optional fields (urban_population,
rural_population, literacy_rate, avg_household_size) are aggregated
when present and skipped otherwise.
"""

import pandas as pd


class RegionAggregator:
    """
    Aggregates subregion-level census data to region level.

    Usage:
        agg = RegionAggregator(df)
        region_df = agg.aggregate()
        print(agg.region_share())
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def aggregate(self) -> pd.DataFrame:
        """Returns one row per region with summed and averaged fields."""
        sum_specs = {
            "total_population": ("total_population", "sum"),
            "male": ("male", "sum"),
            "female": ("female", "sum"),
        }
        if "third_gender" in self.df.columns:
            sum_specs["third_gender"] = ("third_gender", "sum")
        sum_specs["households"] = ("households", "sum")
        for col in ("urban_population", "rural_population"):
            if col in self.df.columns:
                sum_specs[col] = (col, "sum")
        sum_specs["subregion_count"] = ("subregion", "count")

        result = self.df.groupby("region").agg(**sum_specs)

        avg_specs = {}
        if "literacy_rate" in self.df.columns:
            avg_specs["avg_literacy_rate"] = ("literacy_rate", "mean")
        if "avg_household_size" in self.df.columns:
            avg_specs["avg_household_size"] = ("avg_household_size", "mean")
        if avg_specs:
            averaged = self.df.groupby("region").agg(**avg_specs).round(2)
            result = result.join(averaged)

        result = result.reset_index()

        # Derived columns, only when their inputs are available.
        if "urban_population" in result.columns:
            result["urbanization_pct"] = (
                result["urban_population"] / result["total_population"] * 100
            ).round(2)
        result["gender_ratio"] = (result["male"] / result["female"] * 100).round(2)

        return result.sort_values("total_population", ascending=False)

    def region_share(self) -> pd.DataFrame:
        """Each region's share (%) of national population."""
        agg = self.aggregate()
        national_total = agg["total_population"].sum()
        agg["population_share_pct"] = (
            agg["total_population"] / national_total * 100
        ).round(2)
        return agg[["region", "total_population", "population_share_pct"]]

    def most_populous_region(self) -> str:
        agg = self.aggregate()
        return agg.iloc[0]["region"]

    def least_populous_region(self) -> str:
        agg = self.aggregate()
        return agg.iloc[-1]["region"]


# Backward-compatible alias for the pre-refactor name.
ProvinceAggregator = RegionAggregator
