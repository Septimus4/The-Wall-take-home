"""
Common models for The Wall project.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating
    ``created`` and ``modified`` fields.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
