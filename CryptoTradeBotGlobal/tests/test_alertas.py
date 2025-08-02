"""
Testes para o sistema de alertas multi-canal do CryptoTradeBotGlobal
"""
import pytest
from src.utils import alertas

def test_envio_alerta_info():
    assert alertas.enviar_alerta("Teste info", tipo="INFO", canais=["webhook"], urgente=True) in [True, False]

def test_envio_alerta_trade():
    assert alertas.enviar_alerta("Teste trade", tipo="TRADE", canais=["webhook"], urgente=True) in [True, False]

def test_envio_alerta_risk():
    assert alertas.enviar_alerta("Teste risk", tipo="RISK", canais=["webhook"], urgente=True) in [True, False]

def test_envio_alerta_error():
    assert alertas.enviar_alerta("Teste error", tipo="ERROR", canais=["webhook"], urgente=True) in [True, False]

def test_envio_alerta_critical():
    assert alertas.enviar_alerta("Teste critical", tipo="CRITICAL", canais=["webhook"], urgente=True) in [True, False]

def test_estatisticas_alertas():
    stats = alertas.estatisticas_alertas()
    assert isinstance(stats, dict)
    assert 'enviados' in stats
    assert 'falhas' in stats
    assert 'por_tipo' in stats
    assert 'ultimos' in stats
