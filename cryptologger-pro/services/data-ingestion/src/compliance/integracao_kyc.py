"""
Módulo de integração KYC (Know Your Customer).
"""
import requests
from typing import Dict

class KYCProvider:
    """
    Integração com API externa de verificação de identidade.
    """
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def verificar_usuario(self, user_id: str, dados: Dict) -> Dict:
        """Envia dados do usuário para validação KYC."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(f"{self.api_url}/verificar", json=dados, headers=headers)
        return response.json()
