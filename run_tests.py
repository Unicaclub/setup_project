"""
Script de execução autônoma de todos os testes do CryptoLogger Pro.
Inclui logging, cobertura e autoajuste de paths.
"""
import sys
import os
import logging
from pathlib import Path

# Configurar logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/sistema_execucao.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Adicionar src ao sys.path

# Detectar caminho absoluto do src (compatível com Windows)
SRC_PATH = Path(__file__).parent / "cryptologger-pro" / "services" / "data-ingestion" / "src"
if not SRC_PATH.exists():
    # fallback para execução dentro do src
    SRC_PATH = Path(__file__).parent
sys.path.insert(0, str(SRC_PATH.resolve()))

logging.info("Iniciando execução de todos os testes unitários.")

try:
    import pytest
    # Executar pytest em todos os subdiretórios
    # Descobrir todos os arquivos test_*.py recursivamente
    test_files = list(SRC_PATH.rglob("test_*.py"))
    args = [str(f) for f in test_files] + ["--disable-warnings", "-v"]
    result = pytest.main(args)
    if result == 0:
        logging.info("Todos os testes passaram com sucesso.")
    else:
        logging.error(f"Falhas nos testes. Código de saída: {result}")
except Exception as e:
    logging.exception(f"Erro ao executar testes: {e}")

print("Execução de testes finalizada. Verifique logs/sistema_execucao.log para detalhes.")
