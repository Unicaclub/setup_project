"""
Módulo de checagem em tempo real com lista OFAC.
"""
import requests
from typing import Dict

class OFACChecker:
    """
    Checa endereços e nomes contra a lista OFAC.
    """
    def __init__(self, lista_ofac_url: str):
        self.lista_ofac_url = lista_ofac_url
        self.lista_ofac = self._carregar_lista()

    def _carregar_lista(self):
        import os, json
        if self.lista_ofac_url.startswith('http://') or self.lista_ofac_url.startswith('https://'):
            import requests
            response = requests.get(self.lista_ofac_url)
            return response.json().get('enderecos', [])
        else:
            # Caminho local
            caminho = self.lista_ofac_url
            if not os.path.isabs(caminho):
                caminho = os.path.join(os.path.dirname(__file__), '..', 'config', 'lista_sancoes_ofac.json')
                caminho = os.path.abspath(caminho)
            with open(caminho, encoding='utf-8') as f:
                data = json.load(f)
            return data.get('enderecos', [])

    def checar_endereco(self, endereco: str) -> bool:
        """Retorna True se o endereço está na lista OFAC."""
        return endereco in self.lista_ofac
