"""
Testes para motor de alertas.
"""
from ..alerts.motor_alertas import MotorAlertas

def test_gerar_alerta():
    pesos = {"volume": 1.0, "velocidade": 2.0}
    motor = MotorAlertas(pesos)
    indicadores = {"volume": 2, "velocidade": 2}
    info = {"txid": "abc123"}
    alerta = motor.gerar_alerta(indicadores, info)
    assert alerta["nivel"] in ["Baixo", "Médio", "Alto", "Crítico"]
