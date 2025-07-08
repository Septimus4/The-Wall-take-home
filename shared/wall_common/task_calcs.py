"""Task-specific calculations for The Wall construction."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NamedTuple


class WallSection(NamedTuple):
    """Individual wall section with height."""

    initial_height: Decimal  # feet (0-30)
    current_height: Decimal  # feet

    @property
    def is_completed(self) -> bool:
        """Check if section has reached target height of 30 feet."""
        return self.current_height >= Decimal("30")

    @property
    def feet_remaining(self) -> Decimal:
        """Calculate feet remaining to reach 30 feet."""
        if self.is_completed:
            return Decimal("0")
        return Decimal("30") - self.current_height


class TaskWallProfile(NamedTuple):
    """Wall profile with multiple sections as per task requirements."""

    name: str
    sections: list[WallSection]

    def get_active_sections_count(self) -> int:
        """Count sections that still need work."""
        return sum(1 for section in self.sections if not section.is_completed)

    def is_completed(self) -> bool:
        """Check if all sections are completed."""
        return all(section.is_completed for section in self.sections)


# Task constants
ICE_PER_FOOT = Decimal("195")  # cubic yards per foot
COST_PER_CUBIC_YARD = Decimal("1900")  # Gold Dragons per cubic yard


def calculate_daily_ice_usage(profile: TaskWallProfile, day: int) -> Decimal:
    """Calculate ice usage for a specific day.

    Args:
        profile: Wall profile with sections
        day: Day number (1-based)

    Returns:
        Ice usage in cubic yards for that day
    """
    # Simulate the profile state on the given day
    simulated_sections = []

    for section in profile.sections:
        # Calculate height on the given day
        days_of_work = min(day - 1, int(section.feet_remaining))
        current_height = section.initial_height + Decimal(str(days_of_work))

        simulated_sections.append(
            WallSection(
                initial_height=section.initial_height, current_height=current_height
            )
        )

    # Count active sections on this day
    active_sections = sum(1 for s in simulated_sections if not s.is_completed)

    # Each active section adds 1 foot, using 195 cubic yards
    return Decimal(str(active_sections)) * ICE_PER_FOOT


def calculate_daily_cost(profile: TaskWallProfile, day: int) -> Decimal:
    """Calculate cost for a specific day.

    Args:
        profile: Wall profile with sections
        day: Day number (1-based)

    Returns:
        Cost in Gold Dragons for that day
    """
    ice_usage = calculate_daily_ice_usage(profile, day)
    return ice_usage * COST_PER_CUBIC_YARD


def calculate_cumulative_cost(profile: TaskWallProfile, up_to_day: int) -> Decimal:
    """Calculate cumulative cost up to a specific day.

    Args:
        profile: Wall profile with sections
        up_to_day: Day number (1-based)

    Returns:
        Total cost in Gold Dragons up to that day
    """
    total_cost = Decimal("0")

    for day in range(1, up_to_day + 1):
        total_cost += calculate_daily_cost(profile, day)

    return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_completion_days(profile: TaskWallProfile) -> int:
    """Calculate how many days needed to complete the profile.

    Args:
        profile: Wall profile with sections

    Returns:
        Number of days to complete all sections
    """
    if not profile.sections:
        return 0

    max_days = 0
    for section in profile.sections:
        days_needed = int(section.feet_remaining)
        max_days = max(max_days, days_needed)

    return max_days


def parse_profile_input(profile_line: str, profile_name: str = "") -> TaskWallProfile:
    """Parse a profile line into a TaskWallProfile.

    Args:
        profile_line: Space-separated heights (e.g., "21 25 28")
        profile_name: Optional name for the profile

    Returns:
        TaskWallProfile with sections
    """
    heights = [Decimal(h.strip()) for h in profile_line.split() if h.strip()]

    sections = [
        WallSection(initial_height=height, current_height=height) for height in heights
    ]

    name = profile_name or f"Profile with {len(sections)} sections"

    return TaskWallProfile(name=name, sections=sections)


def get_profile_summary(profile: TaskWallProfile) -> dict[str, Any]:
    """Get summary statistics for a profile.

    Returns:
        Dictionary with profile statistics
    """
    total_sections = len(profile.sections)
    completed_sections = sum(1 for s in profile.sections if s.is_completed)
    active_sections = total_sections - completed_sections
    completion_days = calculate_completion_days(profile)

    return {
        "name": profile.name,
        "total_sections": total_sections,
        "completed_sections": completed_sections,
        "active_sections": active_sections,
        "estimated_completion_days": completion_days,
        "is_completed": profile.is_completed(),
    }
