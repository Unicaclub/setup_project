"""
Módulo para checagem de velocidade de transações.
"""
from typing import List, Dict

class ChecagemVelocidade:
    """
    Marca transações repetidas em menos de 5 minutos.
    """
    @staticmethod
    def transacoes_rapidas(transacoes: List[Dict]) -> List[Dict]:
        transacoes_ordenadas = sorted(transacoes, key=lambda x: x['timestamp'])
        alertas = []
        for i in range(1, len(transacoes_ordenadas)):
            delta = transacoes_ordenadas[i]['timestamp'] - transacoes_ordenadas[i-1]['timestamp']
            if delta.total_seconds() < 300:
                alertas.append({"tipo": "Velocidade Suspeita", "tx": transacoes_ordenadas[i]})
        return alertas
