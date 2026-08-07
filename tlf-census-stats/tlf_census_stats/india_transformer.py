"""
india_transformer.py — IndiaCensusTransformer
Parses the actual layout of India's Population census PDF tables (e.g.
Census 2011), which is structurally different from every other South
Asian country this package supports:

  - One column marks each row's admin LEVEL: INDIA / STATE / DISTRICT /
    SUB-DISTRICT / ... A district's row does not contain its state —
    the state name only appears on the STATE row above it, and has to
    be carried down through the rows that follow until the next STATE
    row appears (which may be on a later PDF page).
  - Every entity appears as three consecutive rows: Total, Rural, Urban.
  - Names carry inconsistent trailing footnote markers ("@&", "$", ...)
    — present on some rows for an entity and absent on others.

No column-alias mapping can produce region/subregion out of this shape,
because the association between a district and its state isn't encoded
in any single row — it has to be reconstructed by walking the rows in
order. That's what this transformer does, collapsing the raw structure
into one row per district in the canonical schema tlf-census-stats expects.

As a bonus, since the source table already splits each entity into
Total/Rural/Urban rows, urban_population and rural_population are read
directly from the source rather than derived.
"""

import re
from typing import Dict, List, Tuple

import pandas as pd

_FOOTNOTE_PATTERN = re.compile(r"\s*[@$&#*]+\s*$")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_name(raw) -> str:
    """Strip trailing footnote markers (possibly repeated / combined) and whitespace."""
    if raw is None:
        return raw
    name = str(raw).strip()
    while True:
        stripped = _FOOTNOTE_PATTERN.sub("", name).strip()
        if stripped == name:
            return name
        name = stripped


def normalize_cell(raw) -> str:
    """Collapse embedded newlines/extra whitespace before comparing a cell to a
    known value like 'STATE' or 'TOTAL' — PDF text extraction sometimes splits
    a single logical word across lines."""
    if raw is None:
        return ""
    return _WHITESPACE_PATTERN.sub(" ", str(raw)).strip().upper()


def to_number(raw):
    """Parse a census PDF numeric cell (thousands separators, blanks, 'NA') to float or None."""
    if raw is None:
        return None
    text = str(raw).replace(",", "").strip()
    if text == "" or text.upper() in ("NA", "N/A", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


class IndiaCensusTransformer:
    """
    Usage:
        tables = PDFTableExtractor("india_2011.pdf").extract_all()  # or a page range
        df = IndiaCensusTransformer().transform(tables)
        df.to_csv("data/sample/india_from_pdf.csv", index=False)
        # then: StatsReporter("data/sample/india_from_pdf.csv", country="india").run()

    `transform` accepts a list of raw per-page DataFrames (one call per
    page from PDFTableExtractor is fine — state context is carried
    across the whole list, so a state that spans a page break is still
    handled correctly).
    """

    LEVEL_COL = "India/ State/ Union Territory/ District/ Sub-district"
    NAME_COL = "Name"
    SPLIT_COL = "Total/ Rural/ Urban"
    HOUSEHOLDS_COL = "Number of households"
    POP_COL = "Total Population"
    MALE_COL = "Male Population"
    FEMALE_COL = "Female Population"

    # The fixed header this transformer expects extracted tables to have —
    # pass this as `known_header` to PDFTableExtractor.extract_pages() so
    # headerless continuation pages are parsed correctly (see extract.py).
    EXPECTED_HEADER = [
        LEVEL_COL, NAME_COL, SPLIT_COL, HOUSEHOLDS_COL,
        POP_COL, MALE_COL, FEMALE_COL, "Area (In sq. km)",
    ]

    def transform(self, raw_tables: List[pd.DataFrame]) -> pd.DataFrame:
        current_state = None
        districts: Dict[Tuple[str, str], dict] = {}
        order: List[Tuple[str, str]] = []

        for table in raw_tables:
            missing = [c for c in (self.LEVEL_COL, self.NAME_COL, self.SPLIT_COL) if c not in table.columns]
            if missing:
                raise ValueError(
                    f"IndiaCensusTransformer expected columns {missing} not found in extracted "
                    f"table (found: {list(table.columns)}). The PDF's header row may differ from "
                    f"the expected Census layout."
                )

            for _, row in table.iterrows():
                level = normalize_cell(row.get(self.LEVEL_COL))
                name = clean_name(row.get(self.NAME_COL))
                split = normalize_cell(row.get(self.SPLIT_COL))

                if not name or not name.strip():
                    continue  # blank/artifact row (e.g. a page footer line that slipped in)

                if level == "STATE":
                    current_state = name
                    continue
                if level != "DISTRICT":
                    continue  # skip INDIA totals and SUB-DISTRICT rows — we want district-level
                if current_state is None:
                    continue  # defensive: malformed/header row before any STATE seen

                key = (current_state, name)
                if key not in districts:
                    districts[key] = {}
                    order.append(key)

                if split == "TOTAL":
                    districts[key]["total_population"] = to_number(row.get(self.POP_COL))
                    districts[key]["male"] = to_number(row.get(self.MALE_COL))
                    districts[key]["female"] = to_number(row.get(self.FEMALE_COL))
                    districts[key]["households"] = to_number(row.get(self.HOUSEHOLDS_COL))
                elif split == "URBAN":
                    districts[key]["urban_population"] = to_number(row.get(self.POP_COL))
                elif split == "RURAL":
                    districts[key]["rural_population"] = to_number(row.get(self.POP_COL))

        records = []
        for state, district in order:
            fields = districts[(state, district)]
            records.append({
                "region": state,
                "subregion": district,
                "total_population": fields.get("total_population"),
                "male": fields.get("male"),
                "female": fields.get("female"),
                "households": fields.get("households"),
                "urban_population": fields.get("urban_population"),
                "rural_population": fields.get("rural_population"),
            })

        return pd.DataFrame(records)
