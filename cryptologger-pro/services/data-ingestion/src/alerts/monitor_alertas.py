"""
Monitoramento automatizado de transações e geração de alertas em tempo real.
"""
import time
import logging
from datetime import datetime, timedelta
from core.regras_anomalias import DetectorAnomalias
from compliance.pontuacao_risco import MotorPontuacaoRisco
from compliance.checagem_ofac import OFACChecker
from alerts.classificador_severidade import ClassificadorSeveridade
import os

COOLDOWN_MIN = 60  # segundos

class MonitorAlertas:
    def __init__(self, media_diaria, paises_risco, pesos_score, lista_ofac_url):
        self.detector = DetectorAnomalias(media_diaria, paises_risco)
        self.pontuador = MotorPontuacaoRisco(pesos_score)
        self.ofac = OFACChecker(lista_ofac_url)
        self.classificador = ClassificadorSeveridade()
        self.last_alert = {}  # carteira: timestamp
        self.logger = logging.getLogger("alerts.monitor")
        os.makedirs("logs/alertas", exist_ok=True)

    def processar_transacoes(self, transacoes):
        for tx in transacoes:
            carteira = tx.get("carteira")
            now = datetime.now()
            # Cooldown por carteira
            if carteira in self.last_alert and (now - self.last_alert[carteira]).total_seconds() < COOLDOWN_MIN:
                continue
            alertas = []
            alertas += self.detector.alertas_volume([tx])
            alertas += self.detector.checagem_velocidade([tx])
            if self.ofac.checar_endereco(tx.get("destino", "")):
                alertas.append({"tipo": "OFAC", "tx": tx})
            # Structuring/layering (mock)
            if tx.get("structuring"):
                alertas.append({"tipo": "Structuring", "tx": tx})
            if tx.get("layering"):
                alertas.append({"tipo": "Layering", "tx": tx})
            if alertas:
                score = self.pontuador.calcular_score({"volume": tx.get("valor", 0)})
                nivel = self.classificador.classificar(score)
                alerta = {
                    "carteira": carteira,
                    "score": score,
                    "categoria": alertas[0]["tipo"],
                    "severidade": nivel,
                    "timestamp": now.isoformat(),
                    "txid": tx.get("txid"),
                    "link_historico": f"/historico/{carteira}"
                }
                self.last_alert[carteira] = now
                self.log_alerta(alerta)

    def log_alerta(self, alerta):
        log_path = f"logs/alertas/{datetime.now().date()}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(str(alerta) + "\n")
        self.logger.warning(f"ALERTA: {alerta}")

# Exemplo de uso (mock loop)
if __name__ == "__main__":
    import random
    monitor = MonitorAlertas(1000, ["IR", "KP"], {"volume": 1.0}, "src/config/lista_sancoes_ofac.json")
    while True:
        tx = {
            "carteira": f"wallet{random.randint(1,3)}",
            "valor": random.randint(100, 5000),
            "destino": random.choice(["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "X", "Y"]),
            "txid": f"tx{random.randint(1000,9999)}",
            "structuring": random.choice([True, False]),
            "layering": random.choice([True, False]),
            "timestamp": datetime.now()
        }
        monitor.processar_transacoes([tx])
        time.sleep(5)
