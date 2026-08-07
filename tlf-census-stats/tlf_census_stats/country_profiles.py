"""
country_profiles.py — CountryProfile registry
Defines how each South Asian country's census CSV maps onto the
package's canonical schema, so the same stats modules work for any
of them without touching business logic.

Canonical columns used everywhere downstream:
    region, subregion, total_population, male, female, households,
    urban_population, rural_population, literacy_rate, avg_household_size

Column detection is alias-based: each canonical name has a list of
raw header variants it should match (case/whitespace-insensitive),
so "Population", "Total Population", and "population_total" all
resolve to the same canonical `total_population` column without the
caller having to know exactly which one a given report used.

Not every canonical column is required for every country — some
census reports simply don't publish literacy rate or average
household size in the same table. `required_columns` on each profile
says which columns MUST be present for that country; everything else
in ALL_NUMERIC_COLUMNS is treated as optional and coerced to numeric
only if present.
"""

from dataclasses import dataclass, field
from typing import Dict, List

# The four fields almost every South Asian census publishes at the
# subregion level. Everything else varies by country/report.
BASE_NUMERIC_COLUMNS: List[str] = ["total_population", "male", "female", "households"]

# Published by some countries/reports but not others. third_gender
# covers a country's non-binary census category — e.g. Bangladesh
# publishes "Hijra" counts; other countries in the region use terms
# like "Other". It's optional (not in BASE_NUMERIC_COLUMNS) since not
# every country's data publishes it, and even where a country generally
# does, an individual dataset/sheet selection might not include it.
OPTIONAL_NUMERIC_COLUMNS: List[str] = [
    "urban_population", "rural_population", "literacy_rate", "avg_household_size",
    "third_gender",
]

ALL_NUMERIC_COLUMNS: List[str] = BASE_NUMERIC_COLUMNS + OPTIONAL_NUMERIC_COLUMNS

# Display order for tables/reports — deliberately separate from the
# required/optional split above (which only governs validation, not
# presentation). third_gender sits right after male/female here since
# that's the natural reading order for a gender breakdown, even though
# it's grouped with the "optional" fields for validation purposes.
DISPLAY_ORDER: List[str] = [
    "total_population", "male", "female", "third_gender", "households",
    "urban_population", "rural_population", "literacy_rate", "avg_household_size",
]

# Universal aliases for the numeric fields — applied for every country in
# addition to whatever a specific profile adds for region/subregion labels.
DEFAULT_NUMERIC_ALIASES: Dict[str, List[str]] = {
    "total_population": ["total_population", "total population", "population", "population total"],
    "male": ["male", "male population", "males", "population_male", "population male"],
    "female": ["female", "female population", "females", "population_female", "population female"],
    "households": ["households", "number of households", "total households", "household count", "household total"],
    "urban_population": ["urban_population", "urban population"],
    "rural_population": ["rural_population", "rural population"],
    "literacy_rate": ["literacy_rate", "literacy rate"],
    "avg_household_size": ["avg_household_size", "average household size", "avg hh size", "avg household size"],
    # "hijra" is specific enough to default globally (Bangladesh's term).
    # Deliberately NOT including "other"/"others" here — too generic a
    # word, and real datasets have unrelated columns like "Other
    # Materials" that would false-positive match. A country whose
    # census uses a generic term for this (e.g. Nepal's "Other") should
    # add that as a country-specific alias instead, where the context
    # of that one dataset makes the match safe.
    "third_gender": ["third_gender", "third gender", "hijra", "population_hijra", "population hijra"],
}


def _normalize_header(raw) -> str:
    """Lowercase/strip a raw column header and collapse underscores plus
    repeated whitespace to single spaces, so 'Population_Total',
    'population_total ', and 'Population  Total' all compare equal to
    the 'population total' alias — real-world exports are inconsistent
    about underscores vs spaces in header names."""
    text = str(raw).lower().strip().replace("_", " ")
    return " ".join(text.split())


@dataclass(frozen=True)
class CountryProfile:
    code: str
    country_name: str
    region_label: str       # e.g. "Province", "State", "Division"
    subregion_label: str    # e.g. "District", "Zila", "Upazila"
    # canonical name -> raw header variants, for the admin-level columns
    # (region/subregion). Numeric aliases are supplied by
    # DEFAULT_NUMERIC_ALIASES automatically; add here only to override.
    column_aliases: Dict[str, List[str]] = field(default_factory=dict)
    # Columns that MUST be present for this country's data to load.
    # Defaults to region/subregion plus the four base numeric fields.
    required_columns: List[str] = field(
        default_factory=lambda: ["region", "subregion"] + BASE_NUMERIC_COLUMNS
    )

    def rename_columns(self, df):
        """Rename raw source columns to canonical names via alias matching."""
        combined_aliases: Dict[str, List[str]] = {
            k: list(v) for k, v in DEFAULT_NUMERIC_ALIASES.items()
        }
        for canonical, variants in self.column_aliases.items():
            # Extend rather than replace: a per-country override for a
            # canonical key that DEFAULT_NUMERIC_ALIASES also defines
            # (e.g. adding a dataset-specific "male" variant) should add
            # to the default variants, not drop them.
            combined_aliases.setdefault(canonical, [])
            combined_aliases[canonical] = list(combined_aliases[canonical]) + list(variants)

        rename_map = {}
        for canonical, variants in combined_aliases.items():
            options = {_normalize_header(v) for v in variants}
            for col in df.columns:
                if col in rename_map:
                    continue
                if _normalize_header(col) in options:
                    rename_map[col] = canonical
        return df.rename(columns=rename_map)


COUNTRY_PROFILES: Dict[str, CountryProfile] = {
    "nepal": CountryProfile(
        code="nepal",
        country_name="Nepal",
        region_label="Province",
        subregion_label="District",
        column_aliases={"region": ["province"], "subregion": ["district"]},
    ),
    "india": CountryProfile(
        code="india",
        country_name="India",
        region_label="State",
        subregion_label="District",
        column_aliases={"region": ["state"], "subregion": ["district"]},
    ),
    "bangladesh": CountryProfile(
        code="bangladesh",
        country_name="Bangladesh",
        region_label="Division",
        subregion_label="District",
        column_aliases={
            "region": ["division"],
            "subregion": ["district"],
            # BBS's merged census export prefixes male/female population
            # columns with their source sheet name rather than using a
            # plain "Male"/"Female" header; these two sum exactly to
            # Population_Total in that export, so they're the correct
            # canonical male/female columns to pick out of the sheet's
            # many other male/female-labeled breakdowns (by marital
            # status, religion, etc., which are NOT the district totals).
            "male": ["Type of Dwelling, Sex & Dist_Population_Male_#"],
            "female": ["Type of Dwelling, Sex & Dist_Population_Female_#"],
            "third_gender": ["Type of Dwelling, Sex & Dist_Population_Hijra_#"],
        },
    ),
    "pakistan": CountryProfile(
        code="pakistan",
        country_name="Pakistan",
        region_label="Province",
        subregion_label="District",
        column_aliases={"region": ["province"], "subregion": ["district"]},
    ),
    "sri_lanka": CountryProfile(
        code="sri_lanka",
        country_name="Sri Lanka",
        region_label="Province",
        subregion_label="District",
        column_aliases={"region": ["province"], "subregion": ["district"]},
    ),
    "bhutan": CountryProfile(
        code="bhutan",
        country_name="Bhutan",
        region_label="Dzongkhag",
        subregion_label="Gewog",
        column_aliases={"region": ["dzongkhag"], "subregion": ["gewog"]},
        # Bhutan's gewog-level reports commonly skip household counts.
        required_columns=["region", "subregion", "total_population", "male", "female"],
    ),
}


def get_profile(country: str) -> CountryProfile:
    """Look up a CountryProfile by name (case/space-insensitive)."""
    key = country.strip().lower().replace(" ", "_")
    if key not in COUNTRY_PROFILES:
        raise ValueError(
            f"Unknown country '{country}'. Available: {sorted(COUNTRY_PROFILES)}"
        )
    return COUNTRY_PROFILES[key]
