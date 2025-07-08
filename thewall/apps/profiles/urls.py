"""URL patterns for wall profiles API."""

from django.urls import path

from . import task_views, views

app_name = "profiles"

urlpatterns = [
    # Original Profile CRUD
    path(
        "profiles/",
        views.WallProfileListCreateView.as_view(),
        name="v1-profile-list-create",
    ),
    path(
        "profiles/<uuid:pk>/",
        views.WallProfileDetailView.as_view(),
        name="v1-profile-detail",
    ),
    # Simulation management
    path(
        "profiles/<uuid:profile_id>/simulations/",
        views.SimulationRunListView.as_view(),
        name="v1-simulation-list",
    ),
    path(
        "profiles/<uuid:profile_id>/start-simulation/",
        views.start_simulation,
        name="v1-start-simulation",
    ),
    path(
        "profiles/<uuid:profile_id>/stop-simulation/",
        views.stop_simulation,
        name="v1-stop-simulation",
    ),
    # Original Overview
    path("overview/", views.project_overview, name="v1-project-overview"),
    # Task-specific endpoints
    path(
        "task-profiles/",
        task_views.TaskWallProfileListCreateView.as_view(),
        name="v1-task-profile-list-create",
    ),
    path(
        "task-profiles/<uuid:pk>/",
        task_views.TaskWallProfileDetailView.as_view(),
        name="v1-task-profile-detail",
    ),
    # Task API endpoints as specified in requirements
    path(
        "profiles/<uuid:profile_id>/days/<int:day>/",
        task_views.daily_ice_usage,
        name="v1-daily-ice-usage",
    ),
    path(
        "profiles/<uuid:profile_id>/overview/<int:day>/",
        task_views.profile_overview,
        name="v1-profile-overview-day",
    ),
    path(
        "profiles/<uuid:profile_id>/overview/",
        task_views.profile_overview,
        name="v1-profile-overview",
    ),
    path(
        "profiles/overview/<int:day>/",
        task_views.all_profiles_overview,
        name="v1-all-profiles-overview-day",
    ),
    path(
        "profiles/overview/",
        task_views.all_profiles_overview,
        name="v1-all-profiles-overview",
    ),
    # Config loading endpoint
    path(
        "load-config/",
        task_views.load_profiles_from_config,
        name="v1-load-config",
    ),
]
