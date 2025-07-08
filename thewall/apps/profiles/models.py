"""Django models for wall profiles (UUID primary keys named `id`)."""
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Manager

if TYPE_CHECKING:
    from shared.wall_common.calcs import WallProfile as DomainWallProfile
    from shared.wall_common.task_calcs import TaskWallProfile as DomainTaskWallProfile


class WallProfile(models.Model):
    """Model representing a wall construction profile."""

    id = models.UUIDField(  # noqa: A003
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the wall profile",
    )

    name = models.CharField(
        max_length=255, help_text="Human‑readable name for the wall"
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Wall height in feet",
    )

    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Wall length in feet",
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Wall width in feet",
    )

    ice_thickness = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Ice thickness added per day in feet",
    )

    # Event‑sourcing fields
    external_profile_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="External profile ID from events",
    )
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    # Simulation progress
    last_simulation_day = models.PositiveIntegerField(null=True, blank=True)
    last_simulation_cost = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    last_simulation_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wall_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["created_at"]),
        ]

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def __str__(self) -> str:  # pragma: no cover – human‑readable
        # Use plain ASCII so tests don’t fail on smart punctuation
        return f"{self.name} ({self.height}x{self.length}x{self.width}ft)"

    def to_domain_profile(self) -> "DomainWallProfile":
        """Convert to pure‑domain dataclass used by the simulator."""
        from shared.wall_common.calcs import WallProfile as DomainProfile

        return DomainProfile(
            name=self.name,
            height=self.height,
            length=self.length,
            width=self.width,
            ice_thickness=self.ice_thickness,
        )

    # Related objects type‑hint for Mypy
    if TYPE_CHECKING:  # pragma: no cover
        from django.db.models import Manager as RelatedManager

        from .models import SimulationRun, WallProfile

        simulation_runs: RelatedManager["SimulationRun"]
        profile: WallProfile


class TaskWallProfile(models.Model):
    """Model for task-specific wall profiles with sections."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the wall profile",
    )

    name = models.CharField(
        max_length=255, help_text="Human-readable name for the wall profile"
    )

    # Profile metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        from .models import WallSection

        sections: Manager["WallSection"]

    # Simulation tracking
    current_day = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "task_wall_profiles"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        section_count = self.sections.count()
        return f"{self.name} ({section_count} sections)"

    def get_active_sections_count(self) -> int:
        """Count sections that still need work."""
        return self.sections.filter(current_height__lt=30).count()

    def to_domain_profile(self) -> "DomainTaskWallProfile":
        """Convert to domain TaskWallProfile."""
        from shared.wall_common.task_calcs import (
            TaskWallProfile as DomainProfile,
        )
        from shared.wall_common.task_calcs import (
            WallSection,
        )

        sections = []
        for section in self.sections.all():
            sections.append(
                WallSection(
                    initial_height=section.initial_height,
                    current_height=section.current_height,
                )
            )

        return DomainProfile(name=self.name, sections=sections)


class WallSection(models.Model):
    """Individual wall section within a profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    profile = models.ForeignKey(
        TaskWallProfile, on_delete=models.CASCADE, related_name="sections"
    )

    section_index = models.PositiveIntegerField(
        help_text="0-based index of section within profile"
    )

    initial_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("30"))],
        help_text="Initial height in feet (0-30)",
    )

    current_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("30"))],
        help_text="Current height in feet",
    )

    # Tracking
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "wall_sections"
        ordering = ["profile", "section_index"]
        unique_together = ["profile", "section_index"]

    def __str__(self) -> str:
        return f"Section {self.section_index} ({self.current_height}/{30}ft)"

    @property
    def is_completed(self) -> bool:
        """Check if section has reached 30 feet."""
        return bool(self.current_height >= Decimal("30"))

    @property
    def feet_remaining(self) -> Decimal:
        """Calculate feet remaining to reach 30 feet."""
        if self.is_completed:
            return Decimal("0")
        return Decimal("30") - cast(Decimal, self.current_height)


class SimulationRun(models.Model):
    """Model tracking simulation runs for wall profiles."""

    id = models.UUIDField(  # noqa: A003
        primary_key=True, default=uuid.uuid4, editable=False
    )

    profile = models.ForeignKey(
        "WallProfile", on_delete=models.CASCADE, related_name="simulation_runs"
    )

    days_simulated = models.PositiveIntegerField(default=0)
    current_cumulative_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    current_ice_volume = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    is_active = models.BooleanField(default=True)

    started_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "simulation_runs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["profile", "is_active"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        # ASCII hyphen so tests expect exact string
        return f"Simulation for {cast(WallProfile, self.profile).name} - Day {self.days_simulated}"
