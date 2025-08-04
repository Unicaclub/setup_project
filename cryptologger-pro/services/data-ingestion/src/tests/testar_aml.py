"""
Testes para regras AML.
"""
from ..compliance.regras_aml import AMLRules

def test_structuring():
    transacoes = [
        {"valor": 500, "tipo": "deposito"},
        {"valor": 400, "tipo": "deposito"}
    ]
    aml = AMLRules(transacoes)
    alertas = aml.detectar_structuring()
    assert alertas, "Deveria detectar structuring"
