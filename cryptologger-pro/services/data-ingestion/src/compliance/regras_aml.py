"""
Módulo de regras AML (Anti-Money Laundering).
"""
from typing import List, Dict

class AMLRules:
    """
    Detecta structuring, layering e smurfing em transações.
    """
    def __init__(self, transacoes: List[Dict]):
        self.transacoes = transacoes

    def detectar_structuring(self) -> List[Dict]:
        """Detecta fracionamento de grandes valores em várias transações pequenas."""
        alertas = []
        for tx in self.transacoes:
            if tx.get('valor', 0) < 1000 and tx.get('tipo') == 'deposito':
                alertas.append({"tipo": "Structuring", "tx": tx})
        return alertas

    def detectar_layering(self) -> List[Dict]:
        """Detecta movimentação entre múltiplas contas/carteiras."""
        alertas = []
        destinos = set()
        for tx in self.transacoes:
            if tx.get('destino') in destinos:
                alertas.append({"tipo": "Layering", "tx": tx})
            destinos.add(tx.get('destino'))
        return alertas

    def detectar_smurfing(self) -> List[Dict]:
        """Detecta múltiplos depósitos pequenos em curto período."""
        alertas = []
        pequenos = [tx for tx in self.transacoes if tx.get('valor', 0) < 500]
        if len(pequenos) > 5:
            alertas.append({"tipo": "Smurfing", "transacoes": pequenos})
        return alertas
