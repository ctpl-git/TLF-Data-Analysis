import os

import pandas as pd
import pytest

from tlf_census_stats.india_transformer import IndiaCensusTransformer, clean_name, to_number
from tlf_census_stats.loader import CensusLoader
from tlf_census_stats.report import StatsReporter

LEVEL_COL = "India/ State/ Union Territory/ District/ Sub-district"
COLUMNS = [LEVEL_COL, "Name", "Total/ Rural/ Urban", "Number of households",
           "Total Population", "Male Population", "Female Population", "Area (In sq. km)"]


def row(level, name, split, households, pop, male, female, area="0"):
    return [level, name, split, households, pop, male, female, area]


def page_1_rows():
    """Transcribed from the real india_2011.pdf page 1 (INDIA + J&K state, two districts,
    each with sub-districts that should be ignored by this transformer)."""
    return [
        row("INDIA", "INDIA @&", "Total", "249,501,663", "1,210,854,977", "623,270,258", "587,584,719"),
        row("INDIA", "INDIA $", "Rural", "168,612,897", "833,748,852", "427,781,058", "405,967,794"),
        row("INDIA", "INDIA $", "Urban", "80,888,766", "377,106,125", "195,489,200", "181,616,925"),
        row("STATE", "JAMMU & KASHMIR @&", "Total", "2,119,718", "12,541,302", "6,640,662", "5,900,640"),
        row("STATE", "JAMMU & KASHMIR", "Rural", "1,553,433", "9,108,060", "4,774,477", "4,333,583"),
        row("STATE", "JAMMU & KASHMIR", "Urban", "566,285", "3,433,242", "1,866,185", "1,567,057"),
        row("DISTRICT", "Kupwara", "Total", "113,929", "870,354", "474,190", "396,164"),
        row("DISTRICT", "Kupwara", "Rural", "101,930", "765,625", "412,038", "353,587"),
        row("DISTRICT", "Kupwara", "Urban", "11,999", "104,729", "62,152", "42,577"),
        row("SUB-DISTRICT", "Kupwara", "Total", "63,022", "540,914", "297,837", "243,077"),
        row("SUB-DISTRICT", "Kupwara", "Rural", "56,014", "465,323", "252,856", "212,467"),
        row("SUB-DISTRICT", "Kupwara", "Urban", "7,008", "75,591", "44,981", "30,610"),
        row("SUB-DISTRICT", "Handwara", "Total", "39,485", "269,311", "141,882", "127,429"),
        row("SUB-DISTRICT", "Handwara", "Rural", "37,474", "255,711", "134,503", "121,208"),
        row("SUB-DISTRICT", "Handwara", "Urban", "2,011", "13,600", "7,379", "6,221"),
        row("DISTRICT", "Badgam", "Total", "103,363", "753,745", "398,041", "355,704"),
        row("DISTRICT", "Badgam", "Rural", "89,417", "655,833", "343,385", "312,448"),
        row("DISTRICT", "Badgam", "Urban", "13,946", "97,912", "54,656", "43,256"),
    ]


def page_2_rows_state_continues_without_repeat():
    """
    Simulates a page break happening mid-state: page 2 starts directly with
    more J&K districts (no repeated STATE header row), then moves on to a
    new state. current_state must survive across the page boundary.
    """
    return [
        row("DISTRICT", "Anantnag", "Total", "150,000", "1,000,000", "520,000", "480,000"),
        row("DISTRICT", "Anantnag", "Rural", "130,000", "850,000", "440,000", "410,000"),
        row("DISTRICT", "Anantnag", "Urban", "20,000", "150,000", "80,000", "70,000"),
        row("STATE", "KERALA @&", "Total", "7,000,000", "33,406,061", "16,027,412", "17,378,649"),
        row("STATE", "KERALA", "Rural", "5,000,000", "17,471,135", "8,391,231", "9,079,904"),
        row("STATE", "KERALA", "Urban", "2,000,000", "15,934,926", "7,636,181", "8,298,745"),
        row("DISTRICT", "Ernakulam", "Total", "800,000", "3,282,388", "1,624,996", "1,657,392"),
        row("DISTRICT", "Ernakulam", "Rural", "300,000", "1,200,000", "590,000", "610,000"),
        row("DISTRICT", "Ernakulam", "Urban", "500,000", "2,082,388", "1,034,996", "1,047,392"),
    ]


@pytest.fixture
def raw_tables():
    return [
        pd.DataFrame(page_1_rows(), columns=COLUMNS),
        pd.DataFrame(page_2_rows_state_continues_without_repeat(), columns=COLUMNS),
    ]


class TestCleanName:
    def test_strips_trailing_footnote_markers(self):
        assert clean_name("INDIA @&") == "INDIA"
        assert clean_name("INDIA $") == "INDIA"
        assert clean_name("JAMMU & KASHMIR @&") == "JAMMU & KASHMIR"

    def test_leaves_plain_names_untouched(self):
        assert clean_name("Kupwara") == "Kupwara"
        assert clean_name("JAMMU & KASHMIR") == "JAMMU & KASHMIR"  # the '&' inside the name stays


class TestToNumber:
    def test_strips_thousands_separators(self):
        assert to_number("1,210,854,977") == 1210854977.0

    def test_blank_and_na_become_none(self):
        assert to_number("") is None
        assert to_number("NA") is None
        assert to_number(None) is None


class TestIndiaCensusTransformer:
    def test_produces_one_row_per_district(self, raw_tables):
        df = IndiaCensusTransformer().transform(raw_tables)
        # Kupwara, Badgam, Anantnag, Ernakulam — INDIA/STATE/SUB-DISTRICT rows excluded
        assert len(df) == 4
        assert set(df["subregion"]) == {"Kupwara", "Badgam", "Anantnag", "Ernakulam"}

    def test_state_correctly_associated_with_district(self, raw_tables):
        df = IndiaCensusTransformer().transform(raw_tables)
        kupwara = df[df["subregion"] == "Kupwara"].iloc[0]
        ernakulam = df[df["subregion"] == "Ernakulam"].iloc[0]
        assert kupwara["region"] == "JAMMU & KASHMIR"
        assert ernakulam["region"] == "KERALA"

    def test_state_carries_across_page_boundary(self, raw_tables):
        """Anantnag is on 'page 2' with no repeated STATE row — must still map to J&K."""
        df = IndiaCensusTransformer().transform(raw_tables)
        anantnag = df[df["subregion"] == "Anantnag"].iloc[0]
        assert anantnag["region"] == "JAMMU & KASHMIR"

    def test_total_rural_urban_split_correctly(self, raw_tables):
        df = IndiaCensusTransformer().transform(raw_tables)
        kupwara = df[df["subregion"] == "Kupwara"].iloc[0]
        assert kupwara["total_population"] == 870354.0
        assert kupwara["male"] == 474190.0
        assert kupwara["female"] == 396164.0
        assert kupwara["households"] == 113929.0
        assert kupwara["urban_population"] == 104729.0
        assert kupwara["rural_population"] == 765625.0

    def test_sub_district_and_india_rows_excluded(self, raw_tables):
        df = IndiaCensusTransformer().transform(raw_tables)
        assert "Handwara" not in set(df["subregion"])  # SUB-DISTRICT, not DISTRICT
        assert "INDIA" not in set(df["region"])

    def test_missing_expected_columns_raises_clear_error(self):
        bad_table = pd.DataFrame([["x", "y", "z"]], columns=["a", "b", "c"])
        with pytest.raises(ValueError):
            IndiaCensusTransformer().transform([bad_table])

    def test_blank_name_row_is_skipped(self):
        """An artifact row (e.g. a stray footer line) with no name shouldn't
        produce a phantom district."""
        rows = [
            row("STATE", "PUNJAB", "Total", "1", "1", "1", "1"),
            row("DISTRICT", "", "Total", "1", "1", "1", "1"),
            row("DISTRICT", "Amritsar", "Total", "441,586", "2,490,656", "1,310,075", "1,180,581"),
        ]
        df = IndiaCensusTransformer().transform([pd.DataFrame(rows, columns=COLUMNS)])
        assert len(df) == 1
        assert df.iloc[0]["subregion"] == "Amritsar"

    def test_level_and_split_cells_tolerate_embedded_whitespace(self):
        """PDF extraction sometimes splits a single logical word across an
        embedded newline (e.g. 'SUB-\\nDISTRICT'); level/split matching
        should still work via normalize_cell rather than a bare .strip()."""
        rows = [
            ["STATE", "PUNJAB", "  total  ", "1", "1", "1", "1", "1"],
            ["district", "Amritsar", "Total", "441,586", "2,490,656", "1,310,075", "1,180,581", "1"],
        ]
        df = IndiaCensusTransformer().transform([pd.DataFrame(rows, columns=COLUMNS)])
        assert len(df) == 1
        assert df.iloc[0]["total_population"] == 2490656


class TestIndiaCensusExpectedHeader:
    def test_expected_header_matches_transformer_columns(self):
        assert IndiaCensusTransformer.EXPECTED_HEADER == COLUMNS


class TestIndiaCensusPDFIntegration:
    """
    Full PDF -> PDFTableExtractor(known_header=...) -> IndiaCensusTransformer
    -> CensusLoader('india') -> StatsReporter, against the actual fixture PDF
    that reproduces the real Census PDF's header-once / headerless-continuation
    structure (tlf-data-cleaning/tests/fixtures/india_census_sample.pdf).
    """

    FIXTURE = os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "tlf-data-cleaning", "tests", "fixtures", "india_census_sample.pdf",
    )

    def test_full_pipeline_from_pdf(self, tmp_path):
        tlf_data_cleaning = pytest.importorskip("tlf_data_cleaning")
        fixture_path = os.path.abspath(self.FIXTURE)
        if not os.path.exists(fixture_path):
            pytest.skip("india_census_sample.pdf fixture not available in this environment")

        extractor = tlf_data_cleaning.PDFTableExtractor(fixture_path)
        tables = extractor.extract_pages([1, 2], known_header=IndiaCensusTransformer.EXPECTED_HEADER)
        assert extractor.last_skipped_rows == 0

        df = IndiaCensusTransformer().transform(tables)
        # Fixture has 3 districts (Kupwara, Badgam under J&K; Amritsar under
        # Punjab) split across a headerless page break — see generate_india_fixture.py
        assert len(df) == 3
        assert set(df["region"]) == {"JAMMU & KASHMIR", "PUNJAB"}
        assert set(df["subregion"]) == {"Kupwara", "Badgam", "Amritsar"}

        out_csv = tmp_path / "india_from_pdf.csv"
        df.to_csv(out_csv, index=False)

        loaded = CensusLoader(str(out_csv), country="india").load()
        assert len(loaded) == 3

        StatsReporter(str(out_csv), country="india").run()  # should not raise
