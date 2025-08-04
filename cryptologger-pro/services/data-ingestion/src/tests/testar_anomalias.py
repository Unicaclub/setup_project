"""
Testes para detecção de anomalias.
"""
from ..core.regras_anomalias import DetectorAnomalias
from datetime import datetime, timedelta

def test_alerta_volume():
    detector = DetectorAnomalias(media_diaria=1000, paises_risco=["IR", "KP"])
    transacoes = [
        {"valor": 2000, "timestamp": datetime.now(), "pais_origem": "BR", "pais_destino": "US"},
        {"valor": 1500, "timestamp": datetime.now(), "pais_origem": "BR", "pais_destino": "US"},
        {"valor": 1000, "timestamp": datetime.now(), "pais_origem": "BR", "pais_destino": "US"}
    ]
    alertas = detector.alertas_volume(transacoes)
    assert alertas, "Deveria gerar alerta de volume elevado"

def test_checagem_velocidade():
    detector = DetectorAnomalias(media_diaria=1000, paises_risco=[])
    agora = datetime.now()
    transacoes = [
        {"valor": 100, "timestamp": agora},
        {"valor": 200, "timestamp": agora + timedelta(seconds=100)}
    ]
    alertas = detector.checagem_velocidade(transacoes)
    assert alertas, "Deveria marcar transação rápida"
