"""
Módulo de pontuação de risco para transações e usuários.
"""
from typing import Dict, List

class MotorPontuacaoRisco:
    """
    Calcula score de risco com base em indicadores ponderados.
    """
    def __init__(self, pesos: Dict[str, float]):
        self.pesos = pesos

    def calcular_score(self, indicadores: Dict[str, float]) -> float:
        """Score = soma dos indicadores ponderados."""
        score = 0.0
        for nome, valor in indicadores.items():
            peso = self.pesos.get(nome, 1.0)
            score += valor * peso
        return score

    def classificar_alerta(self, score: float) -> str:
        if score < 3:
            return "Baixo"
        elif score < 6:
            return "Médio"
        elif score < 9:
            return "Alto"
        else:
            return "Crítico"
