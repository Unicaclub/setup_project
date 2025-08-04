"""
Logger centralizado para todos os módulos do CryptoLogger Pro.
"""
import logging
import os
from datetime import datetime
import hashlib

class LoggerModulo:
    def __init__(self, modulo):
        self.modulo = modulo
        os.makedirs(f"logs/{modulo}", exist_ok=True)
        self.log_path = f"logs/{modulo}/{datetime.now().date()}.log"
        self.logger = logging.getLogger(modulo)
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.log_path, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log(self, id_transacao, score_risco, acao, responsavel, extra=None):
        registro = {
            "timestamp": datetime.now().isoformat(),
            "id_transacao": id_transacao,
            "score_risco": score_risco,
            "acao_tomada": acao,
            "responsavel": responsavel,
            "extra": extra or {}
        }
        registro["hash"] = hashlib.sha256(str(registro).encode()).hexdigest()
        self.logger.info(str(registro))
        return registro
