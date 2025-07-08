"""DRF serializers for wall profiles."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from .models import SimulationRun, TaskWallProfile, WallProfile, WallSection


class WallProfileSerializer(serializers.ModelSerializer[WallProfile]):
    """Serializer for WallProfile model."""

    class Meta:
        model = WallProfile
        fields = [
            "id",
            "name",
            "height",
            "length",
            "width",
            "ice_thickness",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_height(self, value: Decimal) -> Decimal:
        """Validate height is positive."""
        if value <= 0:
            raise serializers.ValidationError("Height must be greater than 0")
        return value

    def validate_length(self, value: Decimal) -> Decimal:
        """Validate length is positive."""
        if value <= 0:
            raise serializers.ValidationError("Length must be greater than 0")
        return value

    def validate_width(self, value: Decimal) -> Decimal:
        """Validate width is positive."""
        if value <= 0:
            raise serializers.ValidationError("Width must be greater than 0")
        return value

    def validate_ice_thickness(self, value: Decimal) -> Decimal:
        """Validate ice thickness is positive."""
        if value <= 0:
            raise serializers.ValidationError("Ice thickness must be greater than 0")
        return value

    def validate_name(self, value: str) -> str:
        """Validate name is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()


class WallProfileCreateSerializer(WallProfileSerializer):
    """Serializer for creating wall profiles with validation."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation."""
        attrs = super().validate(attrs)

        # Check reasonable dimensions
        total_volume = attrs["height"] * attrs["length"] * attrs["width"]
        if total_volume > Decimal("1000000"):  # 1 million cubic feet
            raise serializers.ValidationError(
                "Wall volume too large. Consider reducing dimensions."
            )

        # Check daily ice volume is reasonable
        daily_volume = attrs["height"] * attrs["length"] * attrs["ice_thickness"]
        if daily_volume > total_volume:
            raise serializers.ValidationError(
                "Daily ice volume cannot exceed total wall volume"
            )

        return attrs


class SimulationRunSerializer(serializers.ModelSerializer[SimulationRun]):
    """Serializer for SimulationRun model."""

    profile_name = serializers.CharField(source="profile.name", read_only=True)

    class Meta:
        model = SimulationRun
        fields = [
            "id",
            "profile",
            "profile_name",
            "days_simulated",
            "current_cumulative_cost",
            "current_ice_volume",
            "is_active",
            "started_at",
            "last_updated",
        ]
        read_only_fields = [
            "id",
            "days_simulated",
            "current_cumulative_cost",
            "current_ice_volume",
            "started_at",
            "last_updated",
        ]


class ProjectOverviewSerializer(serializers.Serializer[Any]):
    """Serializer for project overview data."""

    total_profiles = serializers.IntegerField()
    active_simulations = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_ice_volume = serializers.DecimalField(max_digits=20, decimal_places=2)

    profiles = serializers.ListField(
        child=serializers.DictField(), help_text="List of profile summaries"
    )


class WallProfileDetailSerializer(WallProfileSerializer):
    """Detailed serializer with calculated fields."""

    estimated_completion_days = serializers.SerializerMethodField()
    total_wall_volume = serializers.SerializerMethodField()
    simulation_status = serializers.SerializerMethodField()

    class Meta(WallProfileSerializer.Meta):
        fields = WallProfileSerializer.Meta.fields + [
            "estimated_completion_days",
            "total_wall_volume",
            "simulation_status",
        ]

    def get_estimated_completion_days(self, obj: WallProfile) -> int:
        """Calculate estimated completion days."""
        from shared.wall_common.calcs import calculate_completion_estimate

        domain_profile = obj.to_domain_profile()
        return calculate_completion_estimate(domain_profile)

    def get_total_wall_volume(self, obj: WallProfile) -> float:
        """Calculate total wall volume."""
        return float(obj.height * obj.length * obj.width)

    def get_simulation_status(self, obj: WallProfile) -> dict[str, Any]:
        """Get current simulation status."""
        active_run = obj.simulation_runs.filter(is_active=True).first()

        if not active_run:
            return {
                "is_running": False,
                "days_simulated": 0,
                "cumulative_cost": 0.0,
                "completion_percentage": 0.0,
            }

        total_volume = self.get_total_wall_volume(obj)
        completion_percentage = float(
            (active_run.current_ice_volume / Decimal(str(total_volume)) * 100)
            if total_volume > 0
            else 0
        )

        return {
            "is_running": True,
            "days_simulated": active_run.days_simulated,
            "cumulative_cost": float(active_run.current_cumulative_cost),
            "completion_percentage": round(completion_percentage, 1),
        }


class WallSectionSerializer(serializers.ModelSerializer[WallSection]):
    """Serializer for WallSection model."""

    is_completed = serializers.ReadOnlyField()
    feet_remaining = serializers.ReadOnlyField()

    class Meta:
        model = WallSection
        fields = [
            "id",
            "section_index",
            "initial_height",
            "current_height",
            "is_completed",
            "feet_remaining",
            "completed_at",
        ]
        read_only_fields = ["id", "completed_at"]


class TaskWallProfileSerializer(serializers.ModelSerializer[TaskWallProfile]):
    """Serializer for TaskWallProfile model."""

    sections = WallSectionSerializer(many=True, read_only=True)
    sections_input = serializers.CharField(
        write_only=True,
        help_text="Space-separated initial heights (e.g., '21 25 28')",
    )
    active_sections_count = serializers.ReadOnlyField(
        source="get_active_sections_count"
    )

    class Meta:
        model = TaskWallProfile
        fields = [
            "id",
            "name",
            "sections",
            "sections_input",
            "active_sections_count",
            "current_day",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "current_day",
            "is_completed",
        ]

    def create(self, validated_data: dict[str, Any]) -> TaskWallProfile:
        """Create profile with sections from input string."""
        sections_input = validated_data.pop("sections_input")
        profile = TaskWallProfile.objects.create(**validated_data)

        # Parse sections input
        heights = [Decimal(h.strip()) for h in sections_input.split() if h.strip()]

        # Create sections
        for index, height in enumerate(heights):
            WallSection.objects.create(
                profile=profile,
                section_index=index,
                initial_height=height,
                current_height=height,
            )

        return profile

    def validate_sections_input(self, value: str) -> str:
        """Validate sections input format."""
        try:
            heights = [Decimal(h.strip()) for h in value.split() if h.strip()]

            if not heights:
                raise serializers.ValidationError(
                    "At least one section height is required"
                )

            if len(heights) > 2000:
                raise serializers.ValidationError("Maximum 2000 sections allowed")

            for height in heights:
                if height < 0 or height > 30:
                    raise serializers.ValidationError(
                        "Heights must be between 0 and 30 feet"
                    )

            return value

        except (ValueError, TypeError) as err:
            raise serializers.ValidationError(
                "Invalid format. Use space-separated numbers (e.g., '21 25 28')"
            ) from err


class DailyIceUsageSerializer(serializers.Serializer[Any]):
    """Serializer for daily ice usage response."""

    day = serializers.IntegerField()
    ice_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_sections = serializers.IntegerField()


class ProfileOverviewSerializer(serializers.Serializer[Any]):
    """Serializer for profile cost overview."""

    day = serializers.IntegerField()
    cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    cumulative_cost = serializers.DecimalField(max_digits=20, decimal_places=2)


class AllProfilesOverviewSerializer(serializers.Serializer[Any]):
    """Serializer for all profiles overview."""

    day = serializers.IntegerField(allow_null=True)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)
    profiles = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of profile summaries with costs",
    )
