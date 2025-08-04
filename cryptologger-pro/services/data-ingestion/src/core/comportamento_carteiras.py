"""
Módulo de análise de comportamento de carteiras.
"""
from typing import List, Dict
import statistics

class AnaliseCarteira:
    """
    Analisa idade, variância e diversidade de destinos de uma carteira.
    """
    def __init__(self, transacoes: List[Dict]):
        self.transacoes = transacoes

    def idade_carteira(self) -> int:
        """Retorna a idade da carteira em dias."""
        datas = [tx['timestamp'] for tx in self.transacoes]
        if not datas:
            return 0
        return (max(datas) - min(datas)).days

    def variancia_transacoes(self) -> float:
        """Calcula a variância dos valores transacionados."""
        valores = [tx['valor'] for tx in self.transacoes]
        if len(valores) < 2:
            return 0.0
        return statistics.variance(valores)

    def diversidade_destinos(self) -> int:
        """Conta quantos destinos únicos a carteira já utilizou."""
        destinos = set(tx['destino'] for tx in self.transacoes)
        return len(destinos)
