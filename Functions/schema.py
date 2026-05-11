from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class DataRole(str, Enum):
    TARGET = "target"
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"


@dataclass
class ColumnMeta:
    dtype: str = "float"
    role: DataRole = DataRole.CONTINUOUS
    units: Optional[str] = None
    description: Optional[str] = None
    allowed_values: Optional[List] = None