"""Test configuration to suppress warnings."""
import warnings

# Suppress pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
warnings.filterwarnings(
    "ignore", message="Support for class-based.*", category=DeprecationWarning
)

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]
