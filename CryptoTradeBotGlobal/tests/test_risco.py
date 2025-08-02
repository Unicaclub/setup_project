"""
Testes para o gestor de risco do CryptoTradeBotGlobal
"""
import pytest
from src.core.gestor_risco import GestorRisco

def test_stop_loss_bloqueio():
    gestor = GestorRisco(limite_stop=0.05, limite_drawdown=0.10)
    gestor.registrar_saldo(10000)
    gestor.registrar_trade('BTCUSDT', -600)  # 6% perda
    assert not gestor.pode_operar()

def test_drawdown_bloqueio():
    gestor = GestorRisco(limite_stop=0.10, limite_drawdown=0.10)
    gestor.registrar_saldo(10000)
    gestor.registrar_saldo(8900)  # 11% perda
    assert not gestor.pode_operar()

def test_resetar():
    gestor = GestorRisco(limite_stop=0.05, limite_drawdown=0.10)
    gestor.registrar_saldo(10000)
    gestor.registrar_trade('BTCUSDT', -600)
    gestor.resetar()
    assert gestor.pode_operar()

def test_status():
    gestor = GestorRisco(limite_stop=0.05, limite_drawdown=0.10)
    gestor.registrar_saldo(10000)
    status = gestor.status()
    assert isinstance(status, dict)
    assert 'saldo_inicial' in status
    assert 'saldo_atual' in status
    assert 'perda_total' in status
    assert 'ordens_bloqueadas' in status
    assert 'perdas_por_posicao' in status
