"""
Unit tests for the petroleum engineering correlations.

These pin the behaviour that was previously wrong, so the specific defects
found in review cannot silently return.
"""

import math

import pytest

from app.services import calculations as calc


class TestBeanCorrelations:
    def test_gilbert_uses_the_published_coefficient(self):
        """
        Gilbert is P = 10 * GLR^0.546 * Q / S^1.89.

        The original code dropped the 10.0 coefficient and subtracted separator
        pressure, which over-predicted rate by roughly an order of magnitude.
        """
        gilbert = calc.BEAN_CORRELATIONS["Gilbert"]
        assert gilbert.a == 10.00
        assert gilbert.b == 0.546
        assert gilbert.c == 1.89

        expected = 10.00 * (749.17 ** 0.546) * 1770 / (32 ** 1.89)
        assert gilbert.wellhead_pressure(1770, 749.17, 32) == pytest.approx(expected)

    def test_separator_pressure_is_not_subtracted(self):
        """The correlation is a function of rate, ratio and bean size only."""
        gilbert = calc.BEAN_CORRELATIONS["Gilbert"]
        pressure = gilbert.wellhead_pressure(1000, 500, 32)
        # A well flowing 1000 stb/d at GLR 500 through a 32/64 bean sits in the
        # hundreds of psig, not the tens it would if Ps were deducted.
        assert 300 < pressure < 900

    def test_liquid_rate_inverts_wellhead_pressure(self):
        for name, correlation in calc.BEAN_CORRELATIONS.items():
            pressure = correlation.wellhead_pressure(1500, 600, 28)
            recovered = correlation.liquid_rate(pressure, 600, 28)
            assert recovered == pytest.approx(1500, rel=1e-9), name

    def test_all_four_models_are_available(self):
        assert set(calc.BEAN_CORRELATIONS) == {"Gilbert", "Ros", "Baxendell", "Achong"}

    def test_default_is_achong(self):
        """Achong fits the field data best; see calculations.DEFAULT_BEAN_MODEL."""
        assert calc.DEFAULT_BEAN_MODEL == "Achong"
        assert calc.get_bean_correlation(None).name == "Achong"

    def test_unknown_model_falls_back_without_raising(self):
        """'SW Ampa' is an in-house model with no published constants."""
        assert calc.get_bean_correlation("SW Ampa").name == "Achong"

    @pytest.mark.parametrize("rate,ratio,bean", [(0, 500, 32), (1000, 0, 32), (1000, 500, 0)])
    def test_non_positive_inputs_return_none(self, rate, ratio, bean):
        gilbert = calc.BEAN_CORRELATIONS["Gilbert"]
        assert gilbert.wellhead_pressure(rate, ratio, bean) is None


class TestFieldDataAgreement:
    """
    Regression against measured UGHE tests.

    Values are taken from the Historical Data sheet of the UGHE workbook.
    Choke correlations on real field data are good to tens of percent, so the
    tolerance is wide - but an order-of-magnitude error like the original bug
    would fail these outright.
    """

    # (gross stb/d, GOR scf/stb, bean 1/64", measured FTHP psig)
    MEASURED = [
        (1069, 461.632687, 20, 1522),
        (1207, 616.542674, 28, 1378),
    ]

    @pytest.mark.parametrize("gross,gor,bean,fthp", MEASURED)
    def test_achong_is_within_half_an_order_of_magnitude(self, gross, gor, bean, fthp):
        achong = calc.BEAN_CORRELATIONS["Achong"]
        predicted = achong.wellhead_pressure(gross, gor, bean)
        assert 0.25 < predicted / fthp < 4.0


class TestCriticalFlow:
    def test_threshold_matches_the_workbook_convention(self):
        """The workbooks compute Critical Flow as FLP * 1.7 exactly."""
        assert calc.CRITICAL_FLOW_RATIO == 1.7
        assert calc.critical_flow_pressure(133.5) == pytest.approx(226.95)

    def test_detects_sub_critical_flow(self):
        assert calc.is_critical_flow(400, 100) is True
        assert calc.is_critical_flow(150, 100) is False
        # Exactly at the threshold counts as critical.
        assert calc.is_critical_flow(170, 100) is True

    def test_missing_downstream_pressure_is_unknown_not_false(self):
        assert calc.critical_flow_pressure(None) is None
        assert calc.is_critical_flow(400, 0) is None


class TestErosional:
    def test_api14e_velocity_formula(self):
        assert calc.erosional_velocity(100.0, 100.0) == pytest.approx(10.0)
        assert calc.erosional_velocity(25.0, 100.0) == pytest.approx(20.0)

    def test_velocity_falls_as_density_rises(self):
        light = calc.erosional_velocity(10.0)
        heavy = calc.erosional_velocity(50.0)
        assert light > heavy

    def test_non_positive_density_returns_none(self):
        assert calc.erosional_velocity(0) is None
        assert calc.erosional_velocity(-5) is None

    def test_mixture_density_is_bounded_by_the_liquid_density(self):
        """
        Adding gas can only lighten the mixture.

        The previous implementation summed Mscf/d gas with stb/d liquid as if
        they were the same unit, which could produce densities outside any
        physical bound.
        """
        no_gas = calc.api14e_mixture_density(
            pressure_psia=1000, temp_f=150, gas_liquid_ratio=0,
            liquid_sg=0.9, gas_sg=0.65)
        some_gas = calc.api14e_mixture_density(
            pressure_psia=1000, temp_f=150, gas_liquid_ratio=500,
            liquid_sg=0.9, gas_sg=0.65)

        assert some_gas < no_gas
        # Pure liquid of SG 0.9 is about 56 lb/ft3.
        assert no_gas == pytest.approx(0.9 * 62.4, rel=0.02)

    def test_pipe_area(self):
        assert calc.pipe_area_sqft(12.0) == pytest.approx(math.pi / 4)
        assert calc.pipe_area_sqft(0) is None

    def test_erosional_rate_scales_with_bore(self):
        common = dict(velocity_fts=30.0, pressure_psia=800, temp_f=150,
                      gas_liquid_ratio=200)
        narrow = calc.erosional_liquid_rate(inner_diameter_in=2.992, **common)
        wide = calc.erosional_liquid_rate(inner_diameter_in=5.921, **common)
        assert wide > narrow


class TestRatios:
    def test_glr_and_gor_are_not_interchangeable(self):
        """
        GOR is per barrel of oil, GLR per barrel of gross liquid.

        Ingestion previously wrote GOR into both columns, so the two trend
        lines were identical by construction.
        """
        gor = calc.gas_oil_ratio(gas_rate_scfd=181_800, oil_rate_stbd=393.82)
        glr = calc.gas_liquid_ratio(gas_rate_scfd=181_800, gross_liquid_stbd=1069)
        assert gor == pytest.approx(461.6, rel=1e-3)
        assert glr == pytest.approx(170.1, rel=1e-3)
        assert gor > glr

    def test_glr_from_gor_matches_the_direct_calculation(self):
        gor = calc.gas_oil_ratio(181_800, 393.82)
        direct = calc.gas_liquid_ratio(181_800, 1069)
        converted = calc.glr_from_gor(gor, bsw_fraction=675.18 / 1069)
        assert converted == pytest.approx(direct, rel=1e-3)

    def test_glr_equals_gor_for_a_dry_well(self):
        assert calc.glr_from_gor(500, 0.0) == pytest.approx(500)

    def test_glr_rejects_an_impossible_water_cut(self):
        assert calc.glr_from_gor(500, 1.0) is None
        assert calc.glr_from_gor(500, -0.1) is None

    def test_api_to_specific_gravity(self):
        assert calc.oil_sg_from_api(10) == pytest.approx(1.0)
        assert calc.oil_sg_from_api(25) == pytest.approx(0.9042, rel=1e-3)

    def test_liquid_sg_is_volume_weighted(self):
        assert calc.liquid_mixture_sg(0.85, 0.0) == pytest.approx(0.85)
        assert calc.liquid_mixture_sg(0.85, 1.0) == pytest.approx(1.02)
        assert calc.liquid_mixture_sg(0.85, 0.5) == pytest.approx((0.85 + 1.02) / 2)


class TestCurveHelpers:
    def test_rate_series_is_ascending_and_bounded(self):
        series = calc.rate_series(5000, points=10, min_rate=100)
        assert len(series) == 10
        assert series[0] == 100
        assert series[-1] == pytest.approx(5000)
        assert series == sorted(series)

    def test_rate_series_survives_absurd_inputs(self):
        assert len(calc.rate_series(0)) >= 2
        assert max(calc.rate_series(10**9)) <= 200_000

    def test_thp_curve_skips_unusable_points(self):
        curve = calc.build_thp_curve(
            calc.BEAN_CORRELATIONS["Gilbert"], glr=500, bean_64ths=32,
            rates=[0, 500, 1000])
        # The zero rate yields no pressure and is dropped.
        assert [p["rate"] for p in curve] == [500, 1000]
        assert curve[1]["thp"] > curve[0]["thp"]
