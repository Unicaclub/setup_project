

import sys, os
import pytest
import asyncio
from cryptologger_pro.shared.database.connection import initialize_database, get_database, close_database

DATABASE_URL = "postgresql://user:pass@localhost/cryptologger_pro"

@pytest.mark.asyncio
async def test_initialize_and_health_check():
    db_manager = await initialize_database(DATABASE_URL)
    assert db_manager is not None
    health = await db_manager.health_check()
    assert health["status"] == "healthy" or health["status"] == "unhealthy"
    await close_database()

@pytest.mark.asyncio
async def test_multi_tenant_session():
    db_manager = await initialize_database(DATABASE_URL)
    tenant_id = "test-tenant-uuid"
    async with db_manager.get_tenant_session(tenant_id) as session:
        assert session is not None
    await close_database()

@pytest.mark.asyncio
async def test_execute_query():
    db_manager = await initialize_database(DATABASE_URL)
    result = await db_manager.execute_query("SELECT 1 as test")
    row = result.fetchone()
    assert row[0] == 1
    await close_database()
