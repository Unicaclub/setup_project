import sys, os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cryptologger-pro', 'services', 'data-ingestion', 'src'))
sys.path.insert(0, src_path)
import subprocess
painel_path = os.path.join(src_path, 'reporting', 'painel_dashboard.py')
if __name__ == "__main__":
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", painel_path], check=True)
    except Exception as e:
        print(f"Erro ao ativar painel: {e}")
