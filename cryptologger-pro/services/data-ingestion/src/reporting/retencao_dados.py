"""
Política de retenção e expurgo de dados.
"""
import time
from typing import List, Dict

class RetencaoDados:
    """
    Armazena dados por 5 anos e expurga automaticamente.
    """
    def __init__(self):
        self.dados = []

    def armazenar(self, registro: Dict):
        registro['timestamp'] = time.time()
        self.dados.append(registro)

    def expurgar(self):
        agora = time.time()
        cinco_anos = 5 * 365 * 24 * 60 * 60
        self.dados = [r for r in self.dados if agora - r['timestamp'] < cinco_anos]
