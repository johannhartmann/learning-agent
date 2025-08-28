#!/usr/bin/env python3
"""Database migration to add lifecycle columns for long-term learning support."""

import asyncio
import os
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg  # type: ignore[import-untyped]


async def add_lifecycle_columns() -> None:
    """Add lifecycle management columns to the memories table."""

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://learning_agent:learning_agent_pass@localhost:5433/learning_memories",
    )

    conn = await asyncpg.connect(database_url)

    try:
        # Check if memories table exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='memories')"
        )

        if not exists:
            print("Memories table doesn't exist yet. Run the application first to create it.")
            return

        # Check if columns already exist
        columns_to_add = [
            ("lifecycle_state", "VARCHAR(20)", "'NEW'"),
            ("last_validated", "TIMESTAMP", "NULL"),
            ("application_count", "INTEGER", "0"),
            ("success_count", "INTEGER", "0"),
            ("failure_count", "INTEGER", "0"),
            ("consecutive_failures", "INTEGER", "0"),
            ("last_failure_reason", "TEXT", "NULL"),
            ("confidence", "FLOAT", "0.5"),
        ]

        for column_name, column_type, default_value in columns_to_add:
            # Check if column exists
            column_exists = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='memories' AND column_name=$1
                )
                """,
                column_name,
            )

            if not column_exists:
                # Add column
                query = f"ALTER TABLE memories ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                await conn.execute(query)
                print(f"✅ Added column: {column_name}")
            else:
                print(f"⏭️  Column already exists: {column_name}")

        # Create index for lifecycle queries
        index_exists = await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_indexes
                WHERE tablename='memories' AND indexname='idx_lifecycle'
            )
            """
        )

        if not index_exists:
            await conn.execute(
                "CREATE INDEX idx_lifecycle ON memories(lifecycle_state, last_validated)"
            )
            print("✅ Created index: idx_lifecycle")
        else:
            print("⏭️  Index already exists: idx_lifecycle")

        print("\n✅ Lifecycle columns migration completed successfully!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(add_lifecycle_columns())
