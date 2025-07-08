#!/usr/bin/env python
"""Test script to validate URL patterns."""

import logging
import os
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Dynamically determine project root (two levels up from this script)
script_path = Path(__file__).resolve()
project_root = script_path.parents[1]  # Adjust as needed

# Add to sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "thewall"))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "thewall.settings.local")

try:
    import django

    django.setup()
    logger.info("✅ Django setup successful")

    from django.urls import reverse

    logger.info("✅ Django URLs imported")

    # Test URL reversal
    test_cases = [
        ("profiles:v1-profile-list-create", "profiles/"),
        ("profiles:v1-project-overview", "overview/"),
    ]

    for url_name, expected_end in test_cases:
        try:
            url = reverse(url_name)
            logger.info(f"✅ {url_name}: {url}")
            if url.endswith(expected_end):
                logger.info(f"   ✓ Correctly ends with '{expected_end}'")
            else:
                logger.warning(
                    f"   ⚠ Expected to end with '{expected_end}', got '{url}'"
                )
        except Exception as e:
            logger.error(f"❌ {url_name}: {e}")

    logger.info("\n📍 Full API endpoints will be:")
    for url_name, _ in test_cases:
        try:
            url = reverse(url_name)
            logger.info(f"  - http://localhost:8000/api/v1{url}")
        except Exception as e:
            logger.error(f"  - Error: {e}")

except Exception as e:
    logger.error(f"❌ Django setup failed: {e}")
    import traceback

    logger.debug(traceback.format_exc())
