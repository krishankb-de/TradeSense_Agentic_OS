"""
Hypothesis profile configuration for TradeSense property-based testing.

This module configures Hypothesis profiles for different testing scenarios:
- default: Standard testing with 1000 examples
- ci: Continuous integration with 500 examples for faster feedback
- thorough: Exhaustive testing with 5000 examples for critical properties
- dev: Development mode with 100 examples for quick iteration

Usage:
    pytest --hypothesis-profile=thorough
"""

from hypothesis import settings, Verbosity

# Default profile: 1000 examples per property
settings.register_profile(
    "default",
    max_examples=1000,
    deadline=None,
    verbosity=Verbosity.normal,
    print_blob=True,
)

# CI profile: Faster testing for continuous integration
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=5000,  # 5 second deadline per example
    verbosity=Verbosity.normal,
    print_blob=True,
)

# Thorough profile: Exhaustive testing for critical properties
settings.register_profile(
    "thorough",
    max_examples=5000,
    deadline=None,
    verbosity=Verbosity.verbose,
    print_blob=True,
)

# Development profile: Quick iteration during development
settings.register_profile(
    "dev",
    max_examples=100,
    deadline=1000,  # 1 second deadline per example
    verbosity=Verbosity.normal,
    print_blob=False,
)

# Load the default profile
settings.load_profile("default")
