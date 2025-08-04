"""
Módulo de detecção de anomalias para transações cripto.
"""
import logging
from typing import List, Dict

class DetectorAnomalias:
    """
    Detecta desvios estatísticos, alertas de volume, velocidade e risco geográfico.
    """
    def __init__(self, media_diaria: float, paises_risco: List[str]):
        self.media_diaria = media_diaria
        self.paises_risco = set(paises_risco)
        self.logger = logging.getLogger(__name__)

    def detectar_desvios(self, transacoes: List[Dict]) -> List[Dict]:
        """Detecta transações fora do padrão estatístico da carteira."""
        alertas = []
        for tx in transacoes:
            if abs(tx['valor'] - self.media_diaria) > 2 * self.media_diaria:
                alertas.append({"tipo": "Desvio Estatístico", "tx": tx})
        return alertas

    def alertas_volume(self, transacoes: List[Dict]) -> List[Dict]:
        """Gera alerta se volume exceder 3x a média diária."""
        total = sum(tx['valor'] for tx in transacoes)
        if total > 3 * self.media_diaria:
            self.logger.warning(f"Volume elevado detectado: {total}")
            return [{"tipo": "Volume Elevado", "total": total}]
        return []

    def checagem_velocidade(self, transacoes: List[Dict]) -> List[Dict]:
        """Marca transações repetidas em menos de 5 minutos."""
        alertas = []
        transacoes_ordenadas = sorted(transacoes, key=lambda x: x['timestamp'])
        for i in range(1, len(transacoes_ordenadas)):
            delta = transacoes_ordenadas[i]['timestamp'] - transacoes_ordenadas[i-1]['timestamp']
            if delta.total_seconds() < 300:
                alertas.append({"tipo": "Velocidade Suspeita", "tx": transacoes_ordenadas[i]})
        return alertas

    def risco_geografico(self, transacoes: List[Dict]) -> List[Dict]:
        """Marca transações de/para países de risco."""
        alertas = []
        for tx in transacoes:
            if tx.get('pais_origem') in self.paises_risco or tx.get('pais_destino') in self.paises_risco:
                alertas.append({"tipo": "Risco Geográfico", "tx": tx})
        return alertas
