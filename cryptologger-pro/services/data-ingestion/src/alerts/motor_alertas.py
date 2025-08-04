"""
Motor de alertas para compliance cripto.
"""
from typing import List, Dict
from compliance.pontuacao_risco import MotorPontuacaoRisco
from alerts.classificador_severidade import ClassificadorSeveridade

class MotorAlertas:
    """
    Gera e classifica alertas com base em regras e score de risco.
    """
    def __init__(self, pesos: Dict[str, float]):
        self.pontuador = MotorPontuacaoRisco(pesos)
        self.classificador = ClassificadorSeveridade()

    def gerar_alerta(self, indicadores: Dict[str, float], info: Dict) -> Dict:
        score = self.pontuador.calcular_score(indicadores)
        nivel = self.classificador.classificar(score)
        alerta = {"score": score, "nivel": nivel, **info}
        return alerta
