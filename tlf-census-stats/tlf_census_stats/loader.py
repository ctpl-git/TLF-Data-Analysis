"""
loader.py — CensusLoader
Loads and validates South Asian census data into a clean DataFrame
with canonical column names, regardless of which country's schema the
source file uses (see country_profiles.py).

Accepts CSV, Excel (.xlsx/.xls), and JSON input — the file type is
detected from the extension and routed to the matching reader, so
callers don't need to know or care which format a given source file
is in before handing it to CensusLoader. PDF is not read directly:
census PDFs need table extraction first, which is out of scope for
this package (see tlf-data-cleaning).

Only a country's `required_columns` must be present to load. Any other
canonical numeric column (see ALL_NUMERIC_COLUMNS) is coerced to
numeric if present and simply skipped if not — a report published
without literacy rate, for instance, still loads fine. A validation
report is printed on every load so it's obvious what was found vs
missing, rather than failing silently or all-or-nothing.
"""

import pandas as pd
from pathlib import Path

from .country_profiles import get_profile, CountryProfile, ALL_NUMERIC_COLUMNS


class CensusFileFormatError(ValueError):
    """Raised when CensusLoader is given a file type it can't read
    (e.g. a raw PDF), rather than a generic ValueError, so callers can
    catch this specifically and show/handle the conversion guidance."""


class CensusLoader:
    """
    Loads census data from a CSV, Excel, or JSON file for a given
    country and normalizes it to canonical columns: region, subregion,
    plus whichever numeric fields that country's data actually has.

    File type is detected from the extension:
        .csv          -> pandas.read_csv
        .xlsx / .xls  -> pandas.read_excel. By default reads ALL sheets
                          and stacks their rows into one DataFrame (the
                          union of every sheet's columns; a cell is NaN
                          on sheets that don't have that column). Pass
                          `sheet=` to restrict to one sheet (name or
                          index) or a specific list of sheets instead.
        .json         -> pandas.read_json (flat list of records,
                          one object per row with the same keys a
                          CSV would have as columns)
        .pdf          -> raises CensusFileFormatError telling the
                          caller to convert it with tlf-data-cleaning
                          first; this package never parses PDFs itself.

    Usage:
        loader = CensusLoader("data/sample/nepal_census_2021.csv", country="nepal")
        df = loader.load()
        loader.validation_report  # list of per-column presence/status after load()

        # Excel — defaults to reading every sheet:
        loader = CensusLoader("bangladesh_census.xlsx", country="bangladesh")

        # Excel — restrict to one sheet (name or index):
        loader = CensusLoader("bangladesh_census.xlsx", country="bangladesh",
                               sheet="Merged_All_Table")

        # Excel — restrict to a specific set of sheets:
        loader = CensusLoader("bangladesh_census.xlsx", country="bangladesh",
                               sheet=["Type of Dwelling_HH & Pop", "Population by Sex, Dist & Loca"])
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

    def __init__(self, filepath: str, country: str = "nepal", sheet=None, merge_on: str = None):
        self.filepath = Path(filepath)
        self.profile: CountryProfile = get_profile(country)
        self.validation_report = []
        # Excel only: None = read every sheet (default); a single sheet
        # name/index, or a list of them, restricts to just those.
        self.sheet = sheet
        # Excel only: if set, multiple sheets are combined via an outer
        # merge on this column (one row per key value) instead of the
        # default row-stack. Unlike tlf-statistical-summary's generic
        # loader, columns are NOT all prefixed with their sheet name —
        # only columns that genuinely collide between sheets are
        # disambiguated. Blanket prefixing would break this package's
        # alias-based column matching (e.g. "Population_Total" needs to
        # stay recognizable as that canonical name when only one sheet
        # actually has it).
        self.merge_on = merge_on

    def load(self) -> pd.DataFrame:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self.filepath}")

        df = self._read_file()
        df = self.profile.rename_columns(df)
        df = self._coalesce_duplicate_columns(df)

        self.validation_report = self._build_validation_report(df)
        self._print_validation_report()

        self._validate_structure(df)
        df = self._clean(df)
        df = self._drop_invalid_rows(df)

        print(
            f"[CensusLoader] Loaded {len(df)} {self.profile.subregion_label.lower()}s "
            f"from {self.filepath.name} ({self.profile.country_name})"
        )
        return df

    def _coalesce_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """After alias-renaming, it's possible for two different raw
        column names (e.g. "Population_Total" in one stacked sheet and
        "Total Population" in another) to both resolve to the same
        canonical name — leaving two columns sharing that name. Since
        each row in a stacked multi-sheet read only has one of them
        actually filled in (the others are NaN from sheets that don't
        have that field), coalesce takes the first non-null value per
        row across the duplicates rather than leaving the ambiguous
        duplicate-named columns in place (which breaks anything
        expecting df[col] to be a Series, not a DataFrame)."""
        if not df.columns.duplicated().any():
            return df

        dupe_names = df.columns[df.columns.duplicated()].unique().tolist()
        print(f"[CensusLoader] Note: {len(dupe_names)} column(s) had more than one raw "
              f"header alias to the same canonical name after combining sheets — "
              f"took the first non-null value per row for each: {dupe_names}")

        deduped = df.loc[:, ~df.columns.duplicated()].copy()
        for name in dupe_names:
            same_named = df.loc[:, df.columns == name]
            deduped[name] = same_named.bfill(axis=1).iloc[:, 0]
        return deduped

    def _read_json(self) -> pd.DataFrame:
        """Reads JSON census data. Accepts the common flat list-of-records
        shape ([{"region": ..., "subregion": ..., ...}, ...], one row per
        object matching CSV columns) as well as a single flat object
        (treated as one row) — some real-world exports (e.g. metadata
        or single-row summaries) come as one JSON object rather than a
        list. Deeply nested JSON isn't handled here; that needs its own
        transformer, the same way India's PDF layout does."""
        import json

        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            return pd.DataFrame([data])
        raise CensusFileFormatError(
            f"'{self.filepath.name}' is valid JSON but not in a shape tlf-census-stats "
            f"can read: expected a list of row-objects or a single flat object, "
            f"got {type(data).__name__}."
        )

    def _read_excel(self) -> pd.DataFrame:
        """Reads Excel data per self.sheet:
            None       -> every sheet in the workbook (default)
            str / int  -> just that one sheet (name or 0-based index)
            list       -> just the listed sheets (names and/or indices)
        Multiple sheets are stacked into one DataFrame (row-wise concat,
        union of columns) by default — each sheet's own columns still go
        through the normal alias-renaming/validation afterwards, so this
        doesn't require the sheets to share a schema, only for the
        region/subregion and numeric columns you need to end up present
        across them.

        If self.merge_on is set instead, sheets are combined side-by-side
        (one row per key value) rather than stacked — see _merge_sheets."""
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
        """Outer-merges every sheet on self.merge_on. Only columns that
        genuinely collide between sheets get renamed (prefixed with
        their sheet name) — a column that appears in just one sheet
        keeps its original name, so it's still recognizable by this
        country's column aliases afterward.

        The merge key is matched case/whitespace-insensitively (e.g.
        --merge-on "district" matches a sheet's actual "District"
        column) — the sheet's own exact column name is kept in the
        merged result, not whatever casing was typed on the command
        line."""
        merged = None
        seen_columns = set()
        disambiguated = []
        skipped = []
        all_columns_seen = set()

        def _norm(s):
            return str(s).strip().lower()

        target = _norm(self.merge_on)

        for sheet_name, df in frames.items():
            all_columns_seen.update(df.columns)
            actual_key = next((c for c in df.columns if _norm(c) == target), None)
            if actual_key is None:
                skipped.append(sheet_name)
                continue

            rename_map = {}
            for c in df.columns:
                if c == actual_key:
                    continue
                if c in seen_columns:
                    rename_map[c] = f"{sheet_name}_{c}"
                    disambiguated.append(f"{c!r} (from {sheet_name!r}) -> {rename_map[c]!r}")
                else:
                    seen_columns.add(c)

            renamed = df.rename(columns=rename_map)
            if actual_key != self.merge_on:
                renamed = renamed.rename(columns={actual_key: self.merge_on})
            merged = renamed if merged is None else merged.merge(renamed, on=self.merge_on, how="outer")

        if merged is None:
            raise ValueError(
                f"None of the selected sheets contain a '{self.merge_on}' column to merge on. "
                f"Columns actually found across the selected sheets: {sorted(all_columns_seen)}"
            )
        if skipped:
            print(f"[CensusLoader] Note: sheet(s) without a '{self.merge_on}' column were "
                  f"skipped from the merge: {skipped}")
        if disambiguated:
            print(f"[CensusLoader] Note: renamed {len(disambiguated)} colliding column(s) to "
                  f"avoid overwriting between sheets (these won't match this country's usual "
                  f"aliases — add a custom alias if one of them should be recognized as a "
                  f"canonical field): {disambiguated}")
        return merged

    def _read_file(self) -> pd.DataFrame:
        """Detects the file type from its extension and reads it with the
        matching pandas reader. Raises CensusFileFormatError for PDFs
        (with guidance to convert first) and for anything else unrecognized."""
        ext = self.filepath.suffix.lower()

        if ext == ".csv":
            return pd.read_csv(self.filepath)

        if ext in (".xlsx", ".xls"):
            return self._read_excel()

        if ext == ".json":
            return self._read_json()

        if ext == ".pdf":
            raise CensusFileFormatError(
                f"Cannot read '{self.filepath.name}' directly: tlf-census-stats does not "
                f"parse PDFs. Use tlf-data-cleaning to extract and convert the PDF's "
                f"tables into a CSV (or Excel/JSON) file first, then load that "
                f"output here instead."
            )

        raise CensusFileFormatError(
            f"Unsupported file type '{ext}' for '{self.filepath.name}'. "
            f"tlf-census-stats reads: {sorted(self.SUPPORTED_EXTENSIONS)}."
        )

    def list_sheets(self) -> list:
        """Returns the sheet names in an Excel workbook, for building an
        interactive sheet-selection prompt. Empty list for non-Excel files."""
        ext = self.filepath.suffix.lower()
        if ext not in (".xlsx", ".xls"):
            return []
        return pd.ExcelFile(self.filepath).sheet_names

    def _build_validation_report(self, df: pd.DataFrame) -> list:
        report = []
        for col in ["region", "subregion"] + ALL_NUMERIC_COLUMNS:
            required = col in self.profile.required_columns
            report.append({
                "column": col,
                "present": col in df.columns,
                "required": required,
            })
        return report

    def _print_validation_report(self):
        print(f"[CensusLoader] Column check for {self.profile.country_name}:")
        for row in self.validation_report:
            if row["present"]:
                mark = "\u2713"
                note = ""
            elif row["required"]:
                mark = "\u2717"
                note = "  (required, missing)"
            else:
                mark = "\u26a0"
                note = "  (optional, missing \u2014 will be skipped)"
            print(f"    {mark} {row['column']}{note}")

    def _validate_structure(self, df: pd.DataFrame):
        """Hard failures only for structural problems — the whole file is
        unusable without these. Row-level data-quality issues (a handful of
        districts with missing/negative population) are handled separately
        in _drop_invalid_rows: real-world government data almost always has
        a few incomplete rows, and one bad district out of hundreds shouldn't
        block the report for everything else."""
        missing = [col for col in self.profile.required_columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"Missing required columns for {self.profile.country_name}: {missing}. "
                f"See the column check above for what was actually found in the source file."
            )

    def _drop_invalid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows with missing or negative total_population, printing a
        clear warning naming each one — instead of aborting the entire load
        over a handful of incomplete rows."""
        null_mask = df["total_population"].isnull()
        if null_mask.any():
            bad = df.loc[null_mask, ["region", "subregion"]].itertuples(index=False, name=None)
            print(
                f"[CensusLoader] WARNING: dropping {int(null_mask.sum())} "
                f"{self.profile.subregion_label.lower()}(s) with missing total_population: "
                f"{list(bad)}"
            )
            df = df.loc[~null_mask]

        negative_mask = df["total_population"] < 0
        if negative_mask.any():
            bad = df.loc[negative_mask, ["region", "subregion"]].itertuples(index=False, name=None)
            print(
                f"[CensusLoader] WARNING: dropping {int(negative_mask.sum())} "
                f"{self.profile.subregion_label.lower()}(s) with negative total_population: "
                f"{list(bad)}"
            )
            df = df.loc[~negative_mask]

        return df.reset_index(drop=True)

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["region"] = df["region"].astype(str).str.strip()
        df["subregion"] = df["subregion"].astype(str).str.strip()
        for col in ALL_NUMERIC_COLUMNS:
            if col not in df.columns:
                continue  # optional column not present in this country's data
            cleaned = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(cleaned, errors="coerce")
        return df
