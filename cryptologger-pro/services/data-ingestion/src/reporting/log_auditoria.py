"""
Módulo de trilha de auditoria para ações e transações.
"""
import hashlib
import time
from typing import Dict, List

class LogAuditoria:
    """
    Loga cada ação, gera hash e timestamp.
    """
    def __init__(self):
        self.logs = []

    def registrar(self, acao: str, dados: Dict):
        registro = {
            "acao": acao,
            "dados": dados,
            "hash": hashlib.sha256(str(dados).encode()).hexdigest(),
            "timestamp": time.time()
        }
        self.logs.append(registro)

    def exportar(self) -> List[Dict]:
        return self.logs
