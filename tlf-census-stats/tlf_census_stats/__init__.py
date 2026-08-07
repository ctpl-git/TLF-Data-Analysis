"""
tlf-census-stats
----------------
Census-specific statistical analysis for South Asian census / population
data. Supports multiple countries (Nepal, India, Bangladesh, Pakistan,
Sri Lanka, Bhutan) via a pluggable CountryProfile schema — see
country_profiles.py. Part of the TLF-Data-Analysis repo, part of the
TLF ("The Living Facts") initiative.
"""

__version__ = "0.1.0"

from .country_profiles import (
    CountryProfile, COUNTRY_PROFILES, get_profile,
    BASE_NUMERIC_COLUMNS, OPTIONAL_NUMERIC_COLUMNS, ALL_NUMERIC_COLUMNS,
)
from .loader import CensusLoader, CensusFileFormatError
from .describe import DataDescriber
from .aggregate import RegionAggregator, ProvinceAggregator
from .rank import SubregionRanker, DistrictRanker
from .outlier import OutlierDetector
from .india_transformer import IndiaCensusTransformer
from .report import StatsReporter

__all__ = [
    "__version__",
    "CountryProfile",
    "COUNTRY_PROFILES",
    "get_profile",
    "BASE_NUMERIC_COLUMNS",
    "OPTIONAL_NUMERIC_COLUMNS",
    "ALL_NUMERIC_COLUMNS",
    "CensusLoader",
    "CensusFileFormatError",
    "DataDescriber",
    "RegionAggregator",
    "ProvinceAggregator",
    "SubregionRanker",
    "DistrictRanker",
    "OutlierDetector",
    "IndiaCensusTransformer",
    "StatsReporter",
]

__version__ = "0.2.0"
