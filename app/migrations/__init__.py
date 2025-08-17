"""
Migration utilities for GremlinsAI database transitions.

This package contains migration scripts and utilities for transitioning
from SQLite to Weaviate with zero downtime and data integrity guarantees.
"""

__version__ = "1.0.0"
__author__ = "GremlinsAI Team"

from .sqlite_to_weaviate import (
    SQLiteToWeaviateMigrator,
    MigrationConfig,
    MigrationResult,
    run_migration
)

__all__ = [
    "SQLiteToWeaviateMigrator",
    "MigrationConfig", 
    "MigrationResult",
    "run_migration"
]
