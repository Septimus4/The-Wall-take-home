"""Health check URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.health_check, name="health"),
    path("ready/", views.readiness_check, name="readiness"),
]
