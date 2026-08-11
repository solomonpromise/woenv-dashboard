"""
Tests for workbook parsing and data normalisation.

These cover the ingestion defects found in review: BSW stored as a fraction,
gas rates mislabelled by a factor of 1000, GOR written into the GLR column,
unnormalised statuses and unbounded test dates.
"""

from datetime import datetime

import pandas as pd
import pytest

from app.services.data_ingestion import (FIELD_CODE_MAP, FIELD_NAMES,
                                         RETIRED_FIELD_CODES,
                                         DataIngestionService, detect_field_code,
                                         looks_like_well_name)
from app.services.well_status import (CLOSED, FLOWING, UNKNOWN,
                                      normalize_production_method,
                                      normalize_status)
from app.services.workbook import (ColumnResolver, parse_envelope_sheet,
                                   parse_erosional_sheet, safe_float, safe_int,
                                   safe_text)


class TestStatusNormalisation:
    @pytest.mark.parametrize("raw", ["FLOWING", "Flowing", "flowing", "OPEN", "Producing"])
    def test_flowing_variants(self, raw):
        assert normalize_status(raw) == FLOWING

    @pytest.mark.parametrize(
        "raw", ["CLOSED", "Closed-in", "CLOSED_LT", "SHUT IN", "shut-in", "SI"])
    def test_closed_variants(self, raw):
        assert normalize_status(raw) == CLOSED

    @pytest.mark.parametrize("raw", ["036L", "", None, float("nan"), "nan", "???"])
    def test_junk_becomes_unknown(self, raw):
        """
        Well-name fragments leak into the status column on misaligned rows.

        Treating '036L' as a status is what let the dashboard report zero
        closed wells while forty-five were closed.
        """
        assert normalize_status(raw) == UNKNOWN

    def test_production_method(self):
        assert normalize_production_method("Natural Flow") == "Natural Flow"
        assert normalize_production_method("GAS LIFT") == "Gas Lift"
        assert normalize_production_method(None) is None


class TestWellNameValidation:
    @pytest.mark.parametrize("name", ["UGHE001T", "UGHW029S", "UTOR003T"])
    def test_accepts_real_conduits(self, name):
        assert looks_like_well_name(name)

    @pytest.mark.parametrize("name", ["UGHW", "UGHE", "", None, "FIELD", "abc"])
    def test_rejects_facility_codes_and_headers(self, name):
        assert not looks_like_well_name(name)


class TestBSWResolution:
    """BSW must always end up as a percentage in the range 0-100."""

    @staticmethod
    def resolve(row: dict):
        frame = pd.DataFrame([row])
        cols = ColumnResolver(frame.columns)
        return DataIngestionService._resolve_bsw(
            frame.iloc[0], cols, oil=None, water=None, gross=None)

    def test_prefers_the_raw_percentage_column(self):
        assert self.resolve({"Raw BSW (%)": 63.16, "BSW (%)": 0.6316}) == pytest.approx(63.16)

    def test_rescales_the_fraction_column(self):
        """'BSW (%)' holds a fraction despite its name."""
        assert self.resolve({"BSW (%)": 0.8629}) == pytest.approx(86.29)

    def test_accepts_a_genuine_percentage(self):
        assert self.resolve({"BSW (%)": 86.29}) == pytest.approx(86.29)

    def test_recomputes_from_rates_when_absent(self):
        frame = pd.DataFrame([{"other": 1}])
        cols = ColumnResolver(frame.columns)
        result = DataIngestionService._resolve_bsw(
            frame.iloc[0], cols, oil=242.667, water=1527.333, gross=1770)
        assert result == pytest.approx(86.29, rel=1e-3)

    def test_returns_none_when_nothing_is_available(self):
        assert self.resolve({"other": 1}) is None


class TestDateParsing:
    def test_parses_a_timestamp(self):
        result = DataIngestionService._parse_date(pd.Timestamp("2025-04-07"))
        assert result == datetime(2025, 4, 7)

    @pytest.mark.parametrize("value", [0, None, float("nan"), "not a date"])
    def test_rejects_unparseable_values(self, value):
        assert DataIngestionService._parse_date(value) is None

    def test_rejects_the_unix_epoch(self):
        """
        A blank date cell parses to 1 Jan 1970 and would otherwise drag every
        trend chart's axis back fifty years.
        """
        assert DataIngestionService._parse_date(pd.Timestamp("1970-01-01")) is None

    def test_rejects_dates_far_in_the_future(self):
        assert DataIngestionService._parse_date(pd.Timestamp("2400-01-01")) is None


class TestFieldDetection:
    @pytest.mark.parametrize("filename,expected", [
        ("abc_UGHE.xlsx", "UGHE"),
        ("abc_UTOR.xlsx", "UTOR"),
        ("abc_UGWest.xlsx", "UGWest"),
        ("mystery.xlsx", "UNKNOWN"),
    ])
    def test_from_filename(self, filename, expected):
        assert detect_field_code(filename) == expected

    def test_facility_column_wins_over_filename(self):
        assert detect_field_code("mystery.xlsx", pd.Series(["UGHE", "UGHE"])) == "UGHE"

    @pytest.mark.parametrize("code", ["OGIN", "YOKRI"])
    def test_retired_fields_are_flagged_not_imported(self, code):
        """
        Retired fields are recognised so the upload can explain itself, rather
        than failing with a generic 'cannot determine field code'.
        """
        assert detect_field_code(f"abc_{code}.xlsx") == f"RETIRED:{code}"
        assert detect_field_code("x.xlsx", pd.Series([code])) == f"RETIRED:{code}"

    def test_retired_codes_are_absent_from_the_active_maps(self):
        for code in RETIRED_FIELD_CODES:
            assert code not in FIELD_CODE_MAP.values()
            assert code not in FIELD_NAMES

    def test_an_active_field_beats_a_retired_one_in_the_same_workbook(self):
        """A UGHE workbook that merely mentions OGIN must still import."""
        assert detect_field_code("UGHE.xlsx", pd.Series(["OGIN", "UGHE"])) == "UGHE"


class TestColumnResolver:
    def test_matching_ignores_case_and_whitespace(self):
        resolver = ColumnResolver(["FTHP (psi)", "Choke_1 (1/64th)"])
        assert resolver.find("fthp (psi)") == "FTHP (psi)"
        assert resolver.find("FTHP  (PSI)") == "FTHP (psi)"
        assert resolver.find("missing") is None

    def test_falls_through_candidates_in_order(self):
        resolver = ColumnResolver(["GOR"])
        assert resolver.find("GOR (scf/stb)", "GOR") == "GOR"


class TestCoercion:
    @pytest.mark.parametrize("value,expected", [
        (1.5, 1.5), ("2.5", 2.5), (None, None), ("abc", None),
        (float("nan"), None), (float("inf"), None),
    ])
    def test_safe_float(self, value, expected):
        assert safe_float(value) == expected

    def test_safe_int_rounds(self):
        assert safe_int(24.0) == 24
        assert safe_int("24") == 24
        assert safe_int(None) is None

    @pytest.mark.parametrize("value", [None, float("nan"), "", "  ", "nan", "None"])
    def test_safe_text_blank_forms(self, value):
        assert safe_text(value) is None

    def test_safe_text_trims(self):
        assert safe_text("  UGHE001T  ") == "UGHE001T"


class TestEnvelopeSheetParsing:
    def test_extracts_curve_points_and_skips_scatter_markers(self):
        """
        Rows without a positive flowline pressure are single-point scatter
        markers for the latest test, not envelope curve points.
        """
        frame = pd.DataFrame([
            ["UGHE043T", None, None, None],
            [None, None, None, None],
            ["Gross", "THP curve", "FLP", "Critical Flow"],
            [250, 133.5, 133.5, 226.95],
            [350, 139.8, 139.8, 237.66],
            [102, 992.0, 0, None],      # scatter marker - dropped
        ])
        parsed = parse_envelope_sheet(frame)

        assert parsed["well_name"] == "UGHE043T"
        assert [p["gross"] for p in parsed["points"]] == [250, 350]
        assert parsed["points"][0]["critical_flow"] == pytest.approx(226.95)

    def test_derives_critical_flow_when_the_column_is_blank(self):
        frame = pd.DataFrame([
            ["UTOR021L", None, None, None],
            ["Gross", "THP curve", "FLP", "Critical Flow"],
            [20, 190.0, 190.0, None],
        ])
        parsed = parse_envelope_sheet(frame)
        assert parsed["points"][0]["critical_flow"] == pytest.approx(190.0 * 1.7)

    def test_missing_header_yields_no_points(self):
        parsed = parse_envelope_sheet(pd.DataFrame([["nothing", "useful"]]))
        assert parsed["points"] == []


class TestErosionalSheetParsing:
    def test_reads_the_results_block_and_ignores_banners(self):
        frame = pd.DataFrame([
            [None, None, None, None, None],
            ["EROSIONAL RATES", None, None, None, None],
            ["Conduit", "Block", "Qerosion", "Tubing Material", "Sand Presence"],
            ["UGHE001T", "K9100X", 3900, "Carbon Steel", "No"],
            ["UGHE005L", "K9500X", 4100, "Carbon Steel", "Yes"],
        ])
        records = {r["well_name"]: r for r in parse_erosional_sheet(frame)}

        assert set(records) == {"UGHE001T", "UGHE005L"}
        assert safe_float(records["UGHE001T"]["q_erosion"]) == 3900
        assert safe_text(records["UGHE005L"]["block"]) == "K9500X"
        # The 'EROSIONAL RATES' banner must not become a well.
        assert "EROSIONAL RATES" not in records

    def test_empty_sheet_is_not_an_error(self):
        assert parse_erosional_sheet(pd.DataFrame()) == []
