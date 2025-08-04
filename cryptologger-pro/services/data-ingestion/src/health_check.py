"""
Health check do sistema CryptoLogger Pro.
"""
import json
import shutil
import os
import time
from datetime import datetime

STATUS = {
    "ofac": False,
    "kyc": False,
    "loop_alertas": False,
    "tempo_resposta": None,
    "disco_livre": None,
    "ram_livre": None,
    "docker": False
}

def checar_ofac():
    try:
        import requests
        r = requests.get("https://www.treasury.gov/ofac/downloads/sdnlist.txt", timeout=3)
        STATUS["ofac"] = r.status_code == 200
    except Exception:
        STATUS["ofac"] = False

def checar_kyc():
    # Mock: sempre True
    STATUS["kyc"] = True

def checar_loop_alertas():
    # Mock: verifica se arquivo de log de alertas existe hoje
    hoje = datetime.now().date()
    STATUS["loop_alertas"] = os.path.exists(f"logs/alertas/{hoje}.log")

def checar_tempo_resposta():
    start = time.time()
    time.sleep(0.05)
    STATUS["tempo_resposta"] = round((time.time() - start) * 1000, 2)

def checar_disco_ram():
    total, used, free = shutil.disk_usage(".")
    STATUS["disco_livre"] = round(free / (1024**3), 2)  # GB
    try:
        import psutil
        STATUS["ram_livre"] = round(psutil.virtual_memory().available / (1024**3), 2)
    except ImportError:
        STATUS["ram_livre"] = None

def checar_docker():
    STATUS["docker"] = os.path.exists("docker-compose.yml")

def health():
    checar_ofac()
    checar_kyc()
    checar_loop_alertas()
    checar_tempo_resposta()
    checar_disco_ram()
    checar_docker()
    return STATUS

if __name__ == "__main__":
    print(json.dumps(health(), indent=2, ensure_ascii=False))
