# Generated by Django 5.2.4 on 2025-07-09 12:40

import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WallProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the wall profile (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human‑readable name for the wall", max_length=255
                    ),
                ),
                (
                    "height",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Wall height in feet",
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "length",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Wall length in feet",
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "width",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Wall width in feet",
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "ice_thickness",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Ice thickness added per day in feet",
                        max_digits=8,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "external_profile_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="External profile ID from events",
                        max_length=255,
                        null=True,
                        unique=True,
                    ),
                ),
                ("created_by", models.CharField(blank=True, max_length=255, null=True)),
                ("updated_by", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "last_simulation_day",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "last_simulation_cost",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=15, null=True
                    ),
                ),
                ("last_simulation_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "wall_profiles",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["name"], name="wall_profil_name_1e8940_idx"),
                    models.Index(
                        fields=["created_at"], name="wall_profil_created_f05bcc_idx"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SimulationRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("days_simulated", models.PositiveIntegerField(default=0)),
                (
                    "current_cumulative_cost",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=15
                    ),
                ),
                (
                    "current_ice_volume",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("0.00"), max_digits=15
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="simulation_runs",
                        to="profiles.wallprofile",
                    ),
                ),
            ],
            options={
                "db_table": "simulation_runs",
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(
                        fields=["profile", "is_active"],
                        name="simulation__profile_3896aa_idx",
                    ),
                    models.Index(
                        fields=["started_at"], name="simulation__started_1c30d1_idx"
                    ),
                ],
            },
        ),
    ]
