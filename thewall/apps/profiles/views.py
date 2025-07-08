"""DRF views for wall profiles."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from shared.wall_common.calcs import get_project_summary
from shared.wall_common.events import ProfileCreated, ProfileUpdated

from .kafka_publisher import get_kafka_publisher
from .models import SimulationRun, WallProfile
from .serializers import (
    ProjectOverviewSerializer,
    SimulationRunSerializer,
    WallProfileCreateSerializer,
    WallProfileDetailSerializer,
    WallProfileSerializer,
)

logger = logging.getLogger(__name__)


class WallProfileListCreateView(generics.ListCreateAPIView[WallProfile]):
    """List all wall profiles or create a new one."""

    queryset = WallProfile.objects.all()

    def get_serializer_class(self) -> type[BaseSerializer[WallProfile]]:
        if self.request.method == "POST":
            return WallProfileCreateSerializer
        return WallProfileSerializer

    def perform_create(self, serializer: BaseSerializer[WallProfile]) -> None:
        """Create wall profile and publish event."""
        with transaction.atomic():
            # Save the profile
            profile = serializer.save()

            # Create initial simulation run
            SimulationRun.objects.create(profile=profile)

            # Publish ProfileCreated event
            try:
                event = ProfileCreated(
                    event_id="",  # Auto-generated
                    timestamp=datetime.now(),
                    event_type="ProfileCreated",
                    profile_id=str(profile.id),  # Use profile_id instead of id
                    name=profile.name,
                    height=profile.height,
                    length=profile.length,
                    width=profile.width,
                    ice_thickness=profile.ice_thickness,
                    created_by=None,  # TODO: Add user tracking
                )

                publisher = get_kafka_publisher()
                success = publisher.publish_profile_created(event)

                if not success:
                    logger.warning(
                        f"Failed to publish ProfileCreated event for {profile.id}"
                    )

            except Exception as e:
                logger.error(f"Error publishing ProfileCreated event: {e}")
                # Don't fail the request for event publishing errors


class WallProfileDetailView(generics.RetrieveUpdateDestroyAPIView[WallProfile]):
    """Retrieve, update or delete a wall profile."""

    queryset = WallProfile.objects.all()
    serializer_class = WallProfileDetailSerializer

    def perform_update(self, serializer: BaseSerializer[WallProfile]) -> None:
        """Update wall profile and publish event."""
        old_profile = self.get_object()

        with transaction.atomic():
            # Save the updated profile
            profile = serializer.save()

            # Check what changed
            changes = {}
            for field in ["name", "height", "length", "width", "ice_thickness"]:
                old_value = getattr(old_profile, field)
                new_value = getattr(profile, field)
                if old_value != new_value:
                    changes[field] = new_value

            # If there are changes, publish event
            if changes:
                try:
                    event = ProfileUpdated(
                        event_id="",  # Auto-generated
                        timestamp=datetime.now(),
                        event_type="ProfileUpdated",
                        profile_id=str(profile.id),
                        **changes,
                        updated_by=None,  # TODO: Add user tracking
                    )

                    publisher = get_kafka_publisher()
                    success = publisher.publish_profile_updated(event)

                    if not success:
                        logger.warning(
                            f"Failed to publish ProfileUpdated event for {profile.id}"
                        )

                except Exception as e:
                    logger.error(f"Error publishing ProfileUpdated event: {e}")


class SimulationRunListView(generics.ListAPIView[SimulationRun]):
    """List simulation runs for a profile."""

    serializer_class = SimulationRunSerializer

    def get_queryset(self) -> Any:
        profile_id = self.kwargs["profile_id"]
        return SimulationRun.objects.filter(profile_id=profile_id)


@api_view(["GET"])
def project_overview(_request: Request) -> Response:
    """Get project overview with aggregated statistics."""
    try:
        # Get aggregated data
        profiles_qs = WallProfile.objects.all()
        simulations_qs = SimulationRun.objects.filter(is_active=True)

        aggregated = simulations_qs.aggregate(
            total_cost=Sum("current_cumulative_cost"),
            total_ice_volume=Sum("current_ice_volume"),
        )

        # Get detailed profile summaries
        profile_summaries = []
        for profile in profiles_qs:
            active_run = profile.simulation_runs.filter(is_active=True).first()
            days_simulated = active_run.days_simulated if active_run else 0

            domain_profile = profile.to_domain_profile()
            summary = get_project_summary(domain_profile, days_simulated)

            profile_summaries.append(
                {
                    "id": str(profile.id),
                    "name": profile.name,
                    "estimated_completion_days": summary["estimated_completion_days"],
                    "days_simulated": days_simulated,
                    "completion_percentage": summary["completion_percentage"],
                    "cumulative_cost": float(active_run.current_cumulative_cost)
                    if active_run
                    else 0.0,
                    "total_wall_volume": summary["total_wall_volume"],
                }
            )

        overview_data = {
            "total_profiles": profiles_qs.count(),
            "active_simulations": simulations_qs.count(),
            "total_cost": aggregated["total_cost"] or Decimal("0.00"),
            "total_ice_volume": aggregated["total_ice_volume"] or Decimal("0.00"),
            "profiles": profile_summaries,
        }

        serializer = ProjectOverviewSerializer(overview_data)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error generating project overview: {e}")
        return Response(
            {"error": "Failed to generate overview"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def start_simulation(_request: Request, profile_id: str) -> Response:
    """Start or restart simulation for a profile."""
    try:
        profile = WallProfile.objects.get(id=profile_id)

        with transaction.atomic():
            # Deactivate existing simulations
            SimulationRun.objects.filter(profile=profile, is_active=True).update(
                is_active=False
            )

            # Create new simulation run
            simulation = SimulationRun.objects.create(profile=profile)

        serializer = SimulationRunSerializer(simulation)

        logger.info(f"Started simulation for profile {profile_id}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except WallProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error starting simulation for {profile_id}: {e}")
        return Response(
            {"error": "Failed to start simulation"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def stop_simulation(_request: Request, profile_id: str) -> Response:
    """Stop active simulation for a profile."""
    try:
        profile = WallProfile.objects.get(id=profile_id)

        updated_count = SimulationRun.objects.filter(
            profile=profile, is_active=True
        ).update(is_active=False)

        if updated_count == 0:
            return Response(
                {"error": "No active simulation found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Stopped simulation for profile {profile_id}")
        return Response({"message": "Simulation stopped"})

    except WallProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error stopping simulation for {profile_id}: {e}")
        return Response(
            {"error": "Failed to stop simulation"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
