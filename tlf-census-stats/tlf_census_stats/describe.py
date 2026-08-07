"""
describe.py — DataDescriber
Generates descriptive statistics for a census dataset, for any
country's admin hierarchy (canonical region/subregion columns).
Optional numeric columns (literacy_rate, avg_household_size,
urban_population, rural_population) are used when present and
skipped otherwise — not every country's data has all of them.
"""

import pandas as pd

from .country_profiles import DISPLAY_ORDER


class DataDescriber:
    """
    Produces summary statistics: mean, median, std, min, max,
    and distribution shape for whichever numeric census columns
    are present in the loaded data.

    Usage:
        describer = DataDescriber(df)
        summary = describer.summary()
        print(describer.gender_ratio())
    """

    NUMERIC_COLS = DISPLAY_ORDER

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _available_numeric_cols(self) -> list:
        return [col for col in self.NUMERIC_COLS if col in self.df.columns]

    def summary(self) -> pd.DataFrame:
        """Descriptive stats table for whichever numeric columns are present."""
        cols = self._available_numeric_cols()
        stats = self.df[cols].describe().T
        stats["median"] = self.df[cols].median()
        stats["skewness"] = self.df[cols].skew()
        stats = stats[["count", "mean", "median", "std", "min", "25%", "75%", "max", "skewness"]]
        return stats.round(2)

    def gender_ratio(self) -> pd.Series:
        """Males per 100 females, by subregion. male/female are always required.
        This is a standard demographic index and intentionally stays
        binary — it doesn't include third_gender since "per 100 females"
        wouldn't have a natural three-way equivalent. See
        gender_composition() for a breakdown that includes third_gender
        when present."""
        ratio = (self.df["male"] / self.df["female"] * 100).round(2)
        return pd.Series(ratio.values, index=self.df["subregion"], name="males_per_100_females")

    def gender_composition(self) -> pd.DataFrame:
        """Percentage share of male/female/third_gender population per
        subregion. Includes a third_gender_pct column only when that
        data is actually present — most countries' data won't have it,
        and even Bangladesh's own data may be missing it depending on
        which sheet(s) were loaded."""
        cols = ["male", "female"]
        total = self.df["male"] + self.df["female"]
        if "third_gender" in self.df.columns:
            cols.append("third_gender")
            total = total + self.df["third_gender"].fillna(0)

        result = pd.DataFrame({"subregion": self.df["subregion"]})
        for col in cols:
            result[f"{col}_pct"] = (self.df[col] / total * 100).round(2)
        return result

    def urbanization_rate(self) -> pd.Series:
        """Percentage of urban population per subregion. Requires urban_population."""
        if "urban_population" not in self.df.columns:
            raise ValueError("urban_population is not present in this dataset.")
        rate = (self.df["urban_population"] / self.df["total_population"] * 100).round(2)
        return pd.Series(rate.values, index=self.df["subregion"], name="urbanization_pct")

    def population_density_proxy(self) -> pd.Series:
        """People per household (proxy for density without area data)."""
        density = (self.df["total_population"] / self.df["households"]).round(2)
        return pd.Series(density.values, index=self.df["subregion"], name="people_per_household")

    def national_totals(self) -> dict:
        """Key national-level aggregates, including only columns actually present."""
        totals = {
            "total_population": int(self.df["total_population"].sum()),
            "total_male": int(self.df["male"].sum()),
            "total_female": int(self.df["female"].sum()),
        }
        if "third_gender" in self.df.columns:
            totals["total_third_gender"] = int(self.df["third_gender"].sum())
        totals["total_households"] = int(self.df["households"].sum())
        if "literacy_rate" in self.df.columns:
            totals["national_literacy_rate"] = round(self.df["literacy_rate"].mean(), 2)
        if "avg_household_size" in self.df.columns:
            totals["avg_household_size"] = round(self.df["avg_household_size"].mean(), 2)
        totals["total_subregions"] = len(self.df)
        totals["total_regions"] = self.df["region"].nunique()
        return totals
