"""
Script para ativar painel em tempo real do CryptoLogger Pro
"""

import subprocess
import sys

if __name__ == "__main__":
    try:
        # Caminho absoluto para o painel
        painel_path = os.path.join(os.path.dirname(__file__), "reporting", "painel_dashboard.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", painel_path], check=True)
    except Exception as e:
        print(f"Erro ao ativar painel: {e}")
