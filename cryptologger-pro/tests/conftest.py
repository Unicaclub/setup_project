# Arquivo de configuração global para pytest
import sys
import os
import pytest

# Garante que o pacote cryptologger_pro seja importável
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
