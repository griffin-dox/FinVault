#!/usr/bin/env python3
"""
Database initialization script for FinVault
Creates all necessary tables in PostgreSQL and adds sample data
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.user import Base as UserBase
from app.models.audit_log import Base as AuditLogBase
from app.models.session import Base as SessionBase
from app.models.transaction import Base as TransactionBase
from app.models import User, Transaction, TransactionStatus
from datetime import datetime, timezone
from sqlalchemy import select, func

# Load environment variables
load_dotenv()

async def create_sample_data(session: AsyncSession):
    """Create sample users and transactions for testing"""
    try:
        print("👤 Creating sample user...")

        # Check if sample user already exists
        stmt = select(User.id).where(User.email == "test@example.com")
        result = await session.execute(stmt)
        existing_user = result.fetchone()

        sample_user = None
        if existing_user:
            sample_user_id = existing_user[0]
            print(f"✅ Sample user already exists with ID: {sample_user_id}")
            # Get the existing user object
            sample_user = await session.get(User, sample_user_id)
        else:
            # Create a sample user
            sample_user = User(
                name="Test User",
                email="test@example.com",
                phone="+1234567890",
                country="US",
                role="user",
                verified=True,
                verified_at=datetime.now(),  # Remove timezone.utc
                onboarding_complete=True
            )

            session.add(sample_user)
            await session.commit()
            await session.refresh(sample_user)
            sample_user_id = sample_user.id
            print(f"✅ Created sample user with ID: {sample_user_id}")

        # Check if transactions already exist for this user
        stmt = select(func.count(Transaction.id)).where(Transaction.user_id == sample_user_id)
        result = await session.execute(stmt)
        txn_count = result.scalar() or 0

        if txn_count > 0:
            print(f"✅ Sample transactions already exist ({txn_count} transactions)")
            return

        # Create sample transactions
        print("💳 Creating sample transactions...")

        transactions = [
            Transaction(
                user_id=sample_user_id,
                amount=10000,  # $100.00
                target_account="checking",
                recipient="sample@example.com",
                device_info='{"browser": "Chrome", "os": "Windows"}',
                location="New York, NY",
                intent="Sample transaction 1",
                description="Sample transfer to checking account",
                risk_score=25,
                status="completed",
                created_at=datetime.now()  # Remove timezone.utc
            ),
            Transaction(
                user_id=sample_user_id,
                amount=5000,  # $50.00
                target_account="savings",
                recipient="savings@example.com",
                device_info='{"browser": "Firefox", "os": "macOS"}',
                location="San Francisco, CA",
                intent="Sample transaction 2",
                description="Sample transfer to savings account",
                risk_score=15,
                status="completed",
                created_at=datetime.now()  # Remove timezone.utc
            ),
            Transaction(
                user_id=sample_user_id,
                amount=25000,  # $250.00
                target_account="checking",
                recipient="checking@example.com",
                device_info='{"browser": "Safari", "os": "iOS"}',
                location="Los Angeles, CA",
                intent="Sample transaction 3",
                description="Sample large transfer",
                risk_score=45,
                status="pending",
                created_at=datetime.now()  # Remove timezone.utc
            )
        ]

        for txn in transactions:
            session.add(txn)

        await session.commit()

        print(f"✅ Created {len(transactions)} sample transactions")

    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        await session.rollback()

async def create_tables():
    """Create all database tables"""

    # Get database URL
    postgres_uri = os.getenv("POSTGRES_URI")
    if not postgres_uri:
        print("❌ POSTGRES_URI not found in environment variables")
        return

    print(f"🔌 Connecting to database: {postgres_uri}")

    # Create engine
    engine = create_async_engine(postgres_uri, echo=True)

    try:
        # Create all tables
        print("📝 Creating tables...")

        # Import all models to ensure they're registered with Base
        from app.models import user, audit_log, session, transaction

        # Create tables
        async with engine.begin() as conn:
            # Create all tables defined in the models
            await conn.run_sync(UserBase.metadata.create_all)
            await conn.run_sync(AuditLogBase.metadata.create_all)
            await conn.run_sync(SessionBase.metadata.create_all)
            await conn.run_sync(TransactionBase.metadata.create_all)

        print("✅ All tables created successfully!")

        # Create sample data
        async with AsyncSession(engine) as session:
            await create_sample_data(session)

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("🚀 Initializing FinVault database...")
    asyncio.run(create_tables())
    print("🎉 Database initialization complete!")
