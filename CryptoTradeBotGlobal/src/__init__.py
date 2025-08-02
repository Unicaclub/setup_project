"""
CryptoTradeBotGlobal - Sistema de Trading de Criptomoedas
Português Brasileiro

Módulo principal do sistema de trading automatizado
"""

__version__ = "1.0.0"
__author__ = "CryptoTradeBotGlobal Team"
__description__ = "Sistema de Trading de Criptomoedas em Português Brasileiro"

# Importações principais
from .core.bot_trading import BotTrading
from .utils.logger import setup_logger

__all__ = [
    'BotTrading',
    'setup_logger'
]
