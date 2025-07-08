"""Core domain calculations for wall simulation."""

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NamedTuple


class DailyStats(NamedTuple):
    """Daily simulation statistics."""

    day: int
    ice_volume: Decimal  # cubic feet
    manpower_hours: Decimal
    material_cost: Decimal  # dollars
    labor_cost: Decimal  # dollars
    total_cost: Decimal  # dollars
    cumulative_cost: Decimal  # dollars


class WallProfile(NamedTuple):
    """Wall construction profile."""

    name: str
    height: Decimal  # feet
    length: Decimal  # feet
    width: Decimal  # feet
    ice_thickness: Decimal  # feet per day


def calculate_daily_ice_volume(profile: WallProfile, _day: int) -> Decimal:
    """Calculate ice volume added on a specific day.

    Formula: height * length * ice_thickness_per_day
    """
    daily_volume = profile.height * profile.length * profile.ice_thickness
    return daily_volume.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_manpower_hours(ice_volume: Decimal) -> Decimal:
    """Calculate manpower hours needed for given ice volume.

    Assumes 0.5 hours per cubic foot of ice handling.
    """
    hours_per_cubic_foot = Decimal("0.5")
    total_hours = ice_volume * hours_per_cubic_foot
    return total_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_material_cost(ice_volume: Decimal) -> Decimal:
    """Calculate material cost for ice processing.

    Includes ice collection, transportation, and binding materials.
    Assumes $2.50 per cubic foot.
    """
    cost_per_cubic_foot = Decimal("2.50")
    total_cost = ice_volume * cost_per_cubic_foot
    return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_labor_cost(manpower_hours: Decimal) -> Decimal:
    """Calculate labor cost based on manpower hours.

    Assumes $15 per hour wage.
    """
    hourly_wage = Decimal("15.00")
    total_cost = manpower_hours * hourly_wage
    return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def simulate_daily_progress(
    profile: WallProfile, day: int, previous_cumulative_cost: Decimal = Decimal("0")
) -> DailyStats:
    """Simulate one day of wall construction progress.

    Args:
        profile: Wall construction profile
        day: Day number (1-based)
        previous_cumulative_cost: Running total from previous days

    Returns:
        DailyStats with all calculated metrics
    """
    ice_volume = calculate_daily_ice_volume(profile, day)
    manpower_hours = calculate_manpower_hours(ice_volume)
    material_cost = calculate_material_cost(ice_volume)
    labor_cost = calculate_labor_cost(manpower_hours)

    total_cost = material_cost + labor_cost
    cumulative_cost = previous_cumulative_cost + total_cost

    return DailyStats(
        day=day,
        ice_volume=ice_volume,
        manpower_hours=manpower_hours,
        material_cost=material_cost,
        labor_cost=labor_cost,
        total_cost=total_cost,
        cumulative_cost=cumulative_cost,
    )


def calculate_completion_estimate(profile: WallProfile) -> int:
    """Estimate days to complete wall construction.

    Based on total wall volume and daily ice volume capacity.
    """
    total_volume = profile.height * profile.length * profile.width
    daily_volume = calculate_daily_ice_volume(profile, 1)

    if daily_volume <= 0:
        return 0

    days = total_volume / daily_volume
    return math.ceil(float(days))


def get_project_summary(profile: WallProfile, days_simulated: int) -> dict[str, Any]:
    """Get project summary statistics.

    Args:
        profile: Wall construction profile
        days_simulated: Number of days already simulated

    Returns:
        Dictionary with project metrics
    """
    estimated_days = calculate_completion_estimate(profile)
    total_volume = profile.height * profile.length * profile.width

    # Calculate cumulative stats for simulated days
    cumulative_cost = Decimal("0")
    cumulative_ice = Decimal("0")

    for day in range(1, days_simulated + 1):
        daily_stats = simulate_daily_progress(profile, day, cumulative_cost)
        cumulative_cost = daily_stats.cumulative_cost
        cumulative_ice += daily_stats.ice_volume

    completion_percentage = (
        float(
            (cumulative_ice / total_volume * 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        )
        if total_volume > 0
        else 0.0
    )

    return {
        "profile_name": profile.name,
        "total_wall_volume": float(total_volume),
        "estimated_completion_days": estimated_days,
        "days_simulated": days_simulated,
        "completion_percentage": completion_percentage,
        "cumulative_cost": float(cumulative_cost),
        "cumulative_ice_volume": float(cumulative_ice),
        "daily_ice_rate": float(profile.ice_thickness),
    }
