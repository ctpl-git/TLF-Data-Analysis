"""
tlf-statistical-summary
A schema-free, generic descriptive-statistics package for any tabular
data (CSV/Excel/JSON). No fixed columns, no domain assumptions — every
grouping/ranking/outlier choice is supplied by the caller (via
arguments or interactive prompts), not inferred from a schema.

For census-specific stats (fixed region/subregion schema, country
profiles, derived metrics like gender ratio), see the separate
tlf-census-stats package instead.
"""

__version__ = "0.1.0"

from .loader import TabularLoader, UnsupportedFileError
from .profiler import ColumnProfiler, ColumnProfile, DatasetProfile
from .describe import Describer
from .rank import Ranker
from .outlier import OutlierDetector
from .aggregate import Aggregator
from .report import Reporter

__all__ = [
    "__version__",
    "TabularLoader",
    "UnsupportedFileError",
    "ColumnProfiler",
    "ColumnProfile",
    "DatasetProfile",
    "Describer",
    "Ranker",
    "OutlierDetector",
    "Aggregator",
    "Reporter",
]
