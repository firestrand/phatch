"""Shared pytest fixtures for Phatch tests."""

# Expose image fixtures via pytest_plugins for convenience if desired.
pytest_plugins = [
    "tests.fixtures.images",
]
