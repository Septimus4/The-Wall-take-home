"""Tests for shared.wall_common.calcs module."""

from decimal import Decimal

import pytest

from shared.wall_common.calcs import (
    DailyStats,
    WallProfile,
    calculate_completion_estimate,
    calculate_daily_ice_volume,
    calculate_labor_cost,
    calculate_manpower_hours,
    calculate_material_cost,
    get_project_summary,
    simulate_daily_progress,
)


class TestWallProfile:
    """Test WallProfile namedtuple."""

    def test_wall_profile_creation(self):
        """Test creating a wall profile."""
        profile = WallProfile(
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2.5"),
        )

        assert profile.name == "Test Wall"
        assert profile.height == Decimal("100")
        assert profile.length == Decimal("200")
        assert profile.width == Decimal("5")
        assert profile.ice_thickness == Decimal("2.5")


class TestCalculations:
    """Test calculation functions."""

    @pytest.fixture
    def sample_profile(self):
        """Sample wall profile for testing."""
        return WallProfile(
            name="Great Wall of Testing",
            height=Decimal("100"),
            length=Decimal("50"),
            width=Decimal("3"),
            ice_thickness=Decimal("2"),
        )

    def test_calculate_daily_ice_volume(self, sample_profile):
        """Test daily ice volume calculation."""
        volume = calculate_daily_ice_volume(sample_profile, 1)

        # height * length * ice_thickness = 100 * 50 * 2 = 10,000
        expected = Decimal("10000.00")
        assert volume == expected

    def test_calculate_daily_ice_volume_precision(self):
        """Test ice volume calculation with decimal precision."""
        profile = WallProfile(
            name="Precision Test",
            height=Decimal("10.5"),
            length=Decimal("20.3"),
            width=Decimal("1"),
            ice_thickness=Decimal("1.7"),
        )

        volume = calculate_daily_ice_volume(profile, 1)
        # 10.5 * 20.3 * 1.7 = 362.355, rounded to 362.36
        expected = Decimal("362.36")
        assert volume == expected

    def test_calculate_manpower_hours(self):
        """Test manpower hours calculation."""
        ice_volume = Decimal("1000")
        hours = calculate_manpower_hours(ice_volume)

        # 1000 * 0.5 = 500 hours
        expected = Decimal("500.00")
        assert hours == expected

    def test_calculate_material_cost(self):
        """Test material cost calculation."""
        ice_volume = Decimal("100")
        cost = calculate_material_cost(ice_volume)

        # 100 * 2.50 = 250.00
        expected = Decimal("250.00")
        assert cost == expected

    def test_calculate_labor_cost(self):
        """Test labor cost calculation."""
        manpower_hours = Decimal("40")
        cost = calculate_labor_cost(manpower_hours)

        # 40 * 15.00 = 600.00
        expected = Decimal("600.00")
        assert cost == expected

    def test_simulate_daily_progress(self, sample_profile):
        """Test daily progress simulation."""
        stats = simulate_daily_progress(sample_profile, 1)

        assert stats.day == 1
        assert stats.ice_volume == Decimal("10000.00")  # 100 * 50 * 2
        assert stats.manpower_hours == Decimal("5000.00")  # 10000 * 0.5
        assert stats.material_cost == Decimal("25000.00")  # 10000 * 2.5
        assert stats.labor_cost == Decimal("75000.00")  # 5000 * 15
        assert stats.total_cost == Decimal("100000.00")  # 25000 + 75000
        assert stats.cumulative_cost == Decimal("100000.00")

    def test_simulate_daily_progress_with_previous_cost(self, sample_profile):
        """Test daily progress with previous cumulative cost."""
        previous_cost = Decimal("50000.00")
        stats = simulate_daily_progress(sample_profile, 2, previous_cost)

        assert stats.day == 2
        assert stats.total_cost == Decimal("100000.00")
        assert stats.cumulative_cost == Decimal("150000.00")  # 50000 + 100000

    def test_calculate_completion_estimate(self, sample_profile):
        """Test completion estimate calculation."""
        days = calculate_completion_estimate(sample_profile)

        # Total volume: 100 * 50 * 3 = 15,000
        # Daily volume: 100 * 50 * 2 = 10,000
        # Days: 15,000 / 10,000 = 1.5, ceiling = 2
        assert days == 2

    def test_calculate_completion_estimate_zero_daily_volume(self):
        """Test completion estimate with zero daily ice thickness."""
        profile = WallProfile(
            name="Zero Ice",
            height=Decimal("100"),
            length=Decimal("50"),
            width=Decimal("3"),
            ice_thickness=Decimal("0"),
        )

        days = calculate_completion_estimate(profile)
        assert days == 0

    def test_get_project_summary_no_simulation(self, sample_profile):
        """Test project summary with no days simulated."""
        summary = get_project_summary(sample_profile, 0)

        expected = {
            "profile_name": "Great Wall of Testing",
            "total_wall_volume": 15000.0,  # 100 * 50 * 3
            "estimated_completion_days": 2,
            "days_simulated": 0,
            "completion_percentage": 0.0,
            "cumulative_cost": 0.0,
            "cumulative_ice_volume": 0.0,
            "daily_ice_rate": 2.0,
        }

        assert summary == expected

    def test_get_project_summary_with_simulation(self, sample_profile):
        """Test project summary with simulated days."""
        summary = get_project_summary(sample_profile, 1)

        # After 1 day: 10,000 ice volume, total volume 15,000
        # Completion: 10,000 / 15,000 = 66.7%
        assert summary["profile_name"] == "Great Wall of Testing"
        assert summary["days_simulated"] == 1
        assert summary["completion_percentage"] == 66.7
        assert summary["cumulative_cost"] == 100000.0
        assert summary["cumulative_ice_volume"] == 10000.0


class TestDailyStats:
    """Test DailyStats namedtuple."""

    def test_daily_stats_creation(self):
        """Test creating daily stats."""
        stats = DailyStats(
            day=1,
            ice_volume=Decimal("1000"),
            manpower_hours=Decimal("500"),
            material_cost=Decimal("2500"),
            labor_cost=Decimal("7500"),
            total_cost=Decimal("10000"),
            cumulative_cost=Decimal("10000"),
        )

        assert stats.day == 1
        assert stats.ice_volume == Decimal("1000")
        assert stats.manpower_hours == Decimal("500")
        assert stats.material_cost == Decimal("2500")
        assert stats.labor_cost == Decimal("7500")
        assert stats.total_cost == Decimal("10000")
        assert stats.cumulative_cost == Decimal("10000")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_dimensions(self):
        """Test calculations with zero dimensions."""
        profile = WallProfile(
            name="Zero Wall",
            height=Decimal("0"),
            length=Decimal("100"),
            width=Decimal("5"),
            ice_thickness=Decimal("2"),
        )

        volume = calculate_daily_ice_volume(profile, 1)
        assert volume == Decimal("0.00")

        stats = simulate_daily_progress(profile, 1)
        assert stats.ice_volume == Decimal("0.00")
        assert stats.total_cost == Decimal("0.00")

    def test_large_numbers(self):
        """Test calculations with large numbers."""
        profile = WallProfile(
            name="Massive Wall",
            height=Decimal("10000"),
            length=Decimal("5000"),
            width=Decimal("10"),
            ice_thickness=Decimal("5"),
        )

        volume = calculate_daily_ice_volume(profile, 1)
        expected = Decimal("250000000.00")  # 10000 * 5000 * 5
        assert volume == expected

        # Ensure calculations don't overflow
        stats = simulate_daily_progress(profile, 1)
        assert stats.ice_volume == expected
        assert stats.total_cost > Decimal("0")

    def test_decimal_precision_maintained(self):
        """Test that decimal precision is maintained throughout calculations."""
        profile = WallProfile(
            name="Precision Wall",
            height=Decimal("12.345"),
            length=Decimal("67.890"),
            width=Decimal("1.111"),
            ice_thickness=Decimal("0.123"),
        )

        volume = calculate_daily_ice_volume(profile, 1)
        # All calculations should maintain precision to 2 decimal places
        assert str(volume).count(".") == 1
        assert len(str(volume).split(".")[1]) <= 2

        stats = simulate_daily_progress(profile, 1)
        assert str(stats.material_cost).count(".") == 1
        assert len(str(stats.material_cost).split(".")[1]) <= 2
