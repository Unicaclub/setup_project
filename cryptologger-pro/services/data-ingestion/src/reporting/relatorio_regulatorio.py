def gerar_relatorio():
    """Gera um relatório simulado para exportação (pode ser substituído por integração real)."""
    # Exemplo de dados simulados
    return [
        {"id": 1, "evento": "Transação suspeita", "valor": 10000, "status": "pendente"},
        {"id": 2, "evento": "Alerta AML", "valor": 5000, "status": "investigando"},
        {"id": 3, "evento": "KYC incompleto", "valor": 0, "status": "falha"}
    ]
"""
Geração de relatórios regulatórios (SAR, AMLD, FATF, etc).
"""
from typing import List, Dict
import json
import csv

class RelatorioRegulatorio:
    """
    Exporta relatórios em formatos exigidos por reguladores.
    """
    def exportar_json(self, dados: List[Dict], caminho: str):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

    def exportar_csv(self, dados: List[Dict], caminho: str):
        if not dados:
            return
        with open(caminho, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dados[0].keys())
            writer.writeheader()
            writer.writerows(dados)
