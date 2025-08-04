"""
Testes unitários para retry.py (CryptoLogger Pro)
"""


import sys, os
import pytest
import asyncio
# Garante que o diretório pai de retry.py está no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from retry import async_retry, sync_retry, RetryError, AsyncRetryManager, retry_stats

# --- Testes para sync_retry ---
def test_sync_retry_success():
    calls = {"count": 0}
    
    @sync_retry(max_attempts=3, delay=0.01)
    def always_succeeds():
        calls["count"] += 1
        return 42
    
    result = always_succeeds()
    assert result == 42
    assert calls["count"] == 1

def test_sync_retry_eventual_success():
    calls = {"count": 0}
    
    @sync_retry(max_attempts=3, delay=0.01)
    def fails_then_succeeds():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("fail")
        return "ok"
    
    result = fails_then_succeeds()
    assert result == "ok"
    assert calls["count"] == 2

def test_sync_retry_failure():
    @sync_retry(max_attempts=2, delay=0.01)
    def always_fails():
        raise RuntimeError("fail")
    
    with pytest.raises(RetryError):
        always_fails()

# --- Testes para async_retry ---
@pytest.mark.asyncio
async def test_async_retry_success():
    calls = {"count": 0}
    
    @async_retry(max_attempts=3, delay=0.01)
    async def always_succeeds():
        calls["count"] += 1
        return 99
    
    result = await always_succeeds()
    assert result == 99
    assert calls["count"] == 1

@pytest.mark.asyncio
async def test_async_retry_eventual_success():
    calls = {"count": 0}
    
    @async_retry(max_attempts=3, delay=0.01)
    async def fails_then_succeeds():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("fail")
        return "ok"
    
    result = await fails_then_succeeds()
    assert result == "ok"
    assert calls["count"] == 2

@pytest.mark.asyncio
async def test_async_retry_failure():
    @async_retry(max_attempts=2, delay=0.01)
    async def always_fails():
        raise RuntimeError("fail")
    
    with pytest.raises(RetryError):
        await always_fails()

# --- Teste para AsyncRetryManager ---
@pytest.mark.asyncio
async def test_async_retry_manager():
    calls = {"count": 0}
    mgr = AsyncRetryManager(max_attempts=3, base_delay=0.01)
    
    async def sometimes_fails():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("fail")
        return "ok"
    
    result = await mgr.execute(sometimes_fails)
    assert result == "ok"
    assert calls["count"] == 2

# --- Teste para RetryStats ---
def test_retry_stats_tracking():
    retry_stats.reset()
    
    tentativas = {"count": 0}
    @sync_retry(max_attempts=2, delay=0.01)
    def fail_uma_vez():
        tentativas["count"] += 1
        if tentativas["count"] == 1:
            raise ValueError("falha")
        return 1

    resultado = fail_uma_vez()
    assert resultado == 1
    stats = retry_stats.get_stats()
    assert stats["total_attempts"] >= 1
    assert stats["successful_attempts"] >= 1
    assert stats["failed_attempts"] >= 0
