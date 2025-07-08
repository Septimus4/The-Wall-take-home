"""Task-specific views for The Wall API."""

import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from shared.wall_common.task_calcs import (
    calculate_completion_days,
    calculate_cumulative_cost,
    calculate_daily_cost,
    calculate_daily_ice_usage,
)

from .models import TaskWallProfile
from .serializers import (
    AllProfilesOverviewSerializer,
    DailyIceUsageSerializer,
    ProfileOverviewSerializer,
    TaskWallProfileSerializer,
)

logger = logging.getLogger(__name__)


class TaskWallProfileListCreateView(generics.ListCreateAPIView[TaskWallProfile]):
    """List all task wall profiles or create a new one."""

    queryset = TaskWallProfile.objects.all()
    serializer_class = TaskWallProfileSerializer


class TaskWallProfileDetailView(generics.RetrieveUpdateDestroyAPIView[TaskWallProfile]):
    """Retrieve, update or delete a task wall profile."""

    queryset = TaskWallProfile.objects.all()
    serializer_class = TaskWallProfileSerializer


@api_view(["GET"])
def daily_ice_usage(_request: Request, profile_id: str, day: int) -> Response:
    """Get ice usage for a specific day for a profile.

    Endpoint: GET /profiles/{profile_id}/days/{day}/
    """
    try:
        profile = TaskWallProfile.objects.get(id=profile_id)
        domain_profile = profile.to_domain_profile()

        ice_amount = calculate_daily_ice_usage(domain_profile, day)

        # Simulate profile state on the given day to get accurate active sections
        simulated_active = 0
        for section in domain_profile.sections:
            days_of_work = min(day - 1, int(section.feet_remaining))
            current_height = section.initial_height + Decimal(str(days_of_work))
            if current_height < 30:
                simulated_active += 1

        data = {
            "day": day,
            "ice_amount": ice_amount,
            "active_sections": simulated_active,
        }

        serializer = DailyIceUsageSerializer(data)
        return Response(serializer.data)

    except TaskWallProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error calculating daily ice usage: {e}")
        return Response(
            {"error": "Failed to calculate ice usage"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def profile_overview(
    _request: Request, profile_id: str, day: int | None = None
) -> Response:
    """Get cost overview for a profile up to a specific day.

    Endpoint: GET /profiles/{profile_id}/overview/{day}/
    """
    try:
        profile = TaskWallProfile.objects.get(id=profile_id)
        domain_profile = profile.to_domain_profile()

        if day is None:
            # Calculate total cost for completed profile
            completion_days = calculate_completion_days(domain_profile)
            day = completion_days

        daily_cost = calculate_daily_cost(domain_profile, day)
        cumulative_cost = calculate_cumulative_cost(domain_profile, day)

        data = {"day": day, "cost": daily_cost, "cumulative_cost": cumulative_cost}

        serializer = ProfileOverviewSerializer(data)
        return Response(serializer.data)

    except TaskWallProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error calculating profile overview: {e}")
        return Response(
            {"error": "Failed to calculate overview"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def all_profiles_overview(_request: Request, day: int | None = None) -> Response:
    """Get overview of all profiles.

    Endpoint: GET /profiles/overview/ or GET /profiles/overview/{day}/
    """
    try:
        profiles = TaskWallProfile.objects.all()
        total_cost = Decimal("0")
        profile_summaries = []

        for profile in profiles:
            domain_profile = profile.to_domain_profile()

            if day is None:
                # Calculate total cost for completed profile
                completion_days = calculate_completion_days(domain_profile)
                profile_cost = calculate_cumulative_cost(
                    domain_profile, completion_days
                )
                profile_day = completion_days
            else:
                profile_cost = calculate_cumulative_cost(domain_profile, day)
                profile_day = day

            total_cost += profile_cost

            profile_summaries.append(
                {
                    "id": str(profile.id),
                    "name": profile.name,
                    "day": profile_day,
                    "cost": profile_cost,
                    "sections_count": profile.sections.count(),
                    "active_sections": profile.get_active_sections_count(),
                }
            )

        data = {"day": day, "total_cost": total_cost, "profiles": profile_summaries}

        serializer = AllProfilesOverviewSerializer(data)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error calculating all profiles overview: {e}")
        return Response(
            {"error": "Failed to calculate overview"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def load_profiles_from_config(request: Request) -> Response:
    """Load wall profiles from config data.

    Expected input:
    {
        "config": [
            "21 25 28",
            "17",
            "17 22 17 19 17"
        ]
    }
    """
    try:
        config_lines = request.data.get("config", [])

        if not config_lines:
            return Response(
                {"error": "Config data is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        created_profiles = []

        with transaction.atomic():
            for i, line in enumerate(config_lines):
                profile_name = f"Profile {i + 1}"

                # Create profile
                profile = TaskWallProfile.objects.create(name=profile_name)

                # Parse and create sections
                try:
                    heights = [Decimal(h.strip()) for h in line.split() if h.strip()]

                    for j, height in enumerate(heights):
                        from .models import WallSection

                        WallSection.objects.create(
                            profile=profile,
                            section_index=j,
                            initial_height=height,
                            current_height=height,
                        )

                    created_profiles.append(
                        {
                            "id": str(profile.id),
                            "name": profile.name,
                            "sections_count": len(heights),
                        }
                    )

                except (ValueError, TypeError):
                    return Response(
                        {"error": f"Invalid data in line {i + 1}: {line}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(
            {
                "message": f"Created {len(created_profiles)} profiles",
                "profiles": created_profiles,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.error(f"Error loading profiles from config: {e}")
        return Response(
            {"error": "Failed to load profiles"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
