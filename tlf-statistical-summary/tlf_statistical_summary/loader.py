"""
loader.py — TabularLoader
Reads a CSV, Excel, or JSON file into a plain pandas DataFrame with no
schema assumptions at all: no required columns, no column renaming,
no notion of what any column "means". Column headers are used exactly
as given in the source file.

This is the schema-free counterpart to tlf-census-stats' CensusLoader —
it does the same file-reading job (same formats, same multi-sheet
Excel support, same PDF rejection) but stops there. Everything after
"here is a DataFrame" — grouping, describing, ranking — is handled by
other modules in this package, driven by columns the user names at
call time rather than a fixed schema.
"""

import json
from pathlib import Path

import pandas as pd


class UnsupportedFileError(ValueError):
    """Raised when the input file's type can't be read at all (e.g. a
    raw PDF, or an extension this package doesn't recognize)."""


class TabularLoader:
    """
    Loads tabular data from a CSV, Excel, or JSON file, as-is.

    File type is detected from the extension:
        .csv          -> pandas.read_csv
        .xlsx / .xls  -> pandas.read_excel. By default reads ALL sheets
                          and stacks their rows into one DataFrame (the
                          union of every sheet's columns; a cell is NaN
                          on sheets that don't have that column). Pass
                          `sheet=` to restrict to one sheet (name or
                          index) or a specific list of sheets instead.

                          If the sheets are actually meant to be
                          combined side-by-side (e.g. one sheet per
                          topic, all keyed by the same "District"
                          column), pass `merge_on=` instead of relying
                          on the stacking default — see below.
        .json         -> a flat list of records ([{...}, {...}]) or a
                          single flat object ({...}), treated as one row
        .pdf          -> raises UnsupportedFileError telling the caller
                          to convert it (e.g. via tlf-data-cleaning)
                          first; this package never parses PDFs itself.

    Usage:
        loader = TabularLoader("weather_stations.csv")
        df = loader.load()

        # Excel — defaults to reading every sheet:
        loader = TabularLoader("data.xlsx")

        # Excel — restrict to one sheet or a specific list of sheets:
        loader = TabularLoader("data.xlsx", sheet="Daily Readings")
        loader = TabularLoader("data.xlsx", sheet=["Sheet1", "Sheet2"])

        # Excel — many sheets, one row per key (e.g. per district) in
        # each, meant to be combined side-by-side rather than stacked:
        loader = TabularLoader("data.xlsx", merge_on="District")
        loader = TabularLoader("data.xlsx", sheet=["Sheet1", "Sheet2"], merge_on="District")
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

    def __init__(self, filepath: str, sheet=None, merge_on: str = None):
        self.filepath = Path(filepath)
        # Excel only: None = read every sheet (default); a single sheet
        # name/index, or a list of them, restricts to just those.
        self.sheet = sheet
        # Excel only: if set, multiple sheets are combined via an outer
        # merge on this column (one row per key value, columns from
        # every sheet side-by-side) instead of the default row-stack.
        # Each sheet's other columns get prefixed with the sheet name
        # to avoid silently colliding with another sheet's same-named
        # column that means something different.
        self.merge_on = merge_on

    def load(self) -> pd.DataFrame:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self.filepath}")
        return self._read_file()

    def _read_file(self) -> pd.DataFrame:
        ext = self.filepath.suffix.lower()

        if ext == ".csv":
            return pd.read_csv(self.filepath)

        if ext in (".xlsx", ".xls"):
            return self._read_excel()

        if ext == ".json":
            return self._read_json()

        if ext == ".pdf":
            raise UnsupportedFileError(
                f"Cannot read '{self.filepath.name}' directly: this package does not "
                f"parse PDFs. Convert the PDF's tables into a CSV/Excel/JSON file "
                f"first (e.g. with tlf-data-cleaning), then load that output here instead."
            )

        raise UnsupportedFileError(
            f"Unsupported file type '{ext}' for '{self.filepath.name}'. "
            f"This package reads: {sorted(self.SUPPORTED_EXTENSIONS)}."
        )

    def _read_excel(self) -> pd.DataFrame:
        result = pd.read_excel(self.filepath, sheet_name=self.sheet)

        if not isinstance(result, dict):
            return result

        frames = {name: df for name, df in result.items() if not df.empty}
        if not frames:
            return pd.DataFrame()

        if self.merge_on:
            return self._merge_sheets(frames)

        return pd.concat(list(frames.values()), ignore_index=True, sort=False)

    def _merge_sheets(self, frames: dict) -> pd.DataFrame:
        """Outer-merges every sheet on self.merge_on, prefixing each
        sheet's other columns with the sheet name first (so e.g.
        "Population_Total" in a Household sheet and a Literacy sheet
        don't collide and silently overwrite/blend into each other —
        they become "Household_Population_Total" and
        "Literacy_Population_Total")."""
        merged = None
        skipped = []
        for sheet_name, df in frames.items():
            if self.merge_on not in df.columns:
                skipped.append(sheet_name)
                continue
            prefixed = df.rename(
                columns={c: f"{sheet_name}_{c}" for c in df.columns if c != self.merge_on}
            )
            merged = prefixed if merged is None else merged.merge(prefixed, on=self.merge_on, how="outer")

        if merged is None:
            raise ValueError(
                f"None of the selected sheets contain a '{self.merge_on}' column to merge on."
            )
        if skipped:
            print(f"[TabularLoader] Note: sheet(s) without a '{self.merge_on}' column were "
                  f"skipped from the merge: {skipped}")
        return merged

    def _read_json(self) -> pd.DataFrame:
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            return pd.DataFrame([data])
        raise UnsupportedFileError(
            f"'{self.filepath.name}' is valid JSON but not in a shape this package "
            f"can read: expected a list of row-objects or a single flat object, "
            f"got {type(data).__name__}."
        )

    def list_sheets(self) -> list:
        """Returns the sheet names in an Excel workbook, for building an
        interactive sheet-selection prompt. Empty list for non-Excel files."""
        ext = self.filepath.suffix.lower()
        if ext not in (".xlsx", ".xls"):
            return []
        return pd.ExcelFile(self.filepath).sheet_names
