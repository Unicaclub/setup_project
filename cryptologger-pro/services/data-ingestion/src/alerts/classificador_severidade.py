"""
Classificador de severidade de alertas.
"""
class ClassificadorSeveridade:
    """
    Classifica score de risco em níveis de severidade.
    """
    def classificar(self, score: float) -> str:
        if score < 3:
            return "Baixo"
        elif score < 6:
            return "Médio"
        elif score < 9:
            return "Alto"
        else:
            return "Crítico"
