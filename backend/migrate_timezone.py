#!/usr/bin/env python3
"""
Database migration script to fix timezone issues in production
Updates datetime columns to be timezone-aware
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Load environment variables
load_dotenv()

async def migrate_timezone_columns():
    """Migrate existing datetime columns to be timezone-aware"""
    postgres_uri = os.getenv("POSTGRES_URI")
    if not postgres_uri:
        print("❌ POSTGRES_URI not found in environment")
        return

    print("🔄 Starting timezone migration...")

    engine = create_async_engine(postgres_uri, echo=True)

    try:
        async with engine.begin() as conn:
            # Update transactions table
            print("📅 Updating transactions.created_at column...")
            await conn.execute(text("""
                ALTER TABLE transactions
                ALTER COLUMN created_at TYPE TIMESTAMPTZ
                USING created_at AT TIME ZONE 'UTC';
            """))

            # Update users table
            print("👤 Updating users.verified_at column...")
            await conn.execute(text("""
                ALTER TABLE users
                ALTER COLUMN verified_at TYPE TIMESTAMPTZ
                USING verified_at AT TIME ZONE 'UTC';
            """))

            # Update audit_logs table
            print("📋 Updating audit_logs.timestamp column...")
            await conn.execute(text("""
                ALTER TABLE audit_logs
                ALTER COLUMN timestamp TYPE TIMESTAMPTZ
                USING timestamp AT TIME ZONE 'UTC';
            """))

            print("✅ Timezone migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_timezone_columns())
