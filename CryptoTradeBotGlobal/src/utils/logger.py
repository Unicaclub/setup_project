"""
CryptoTradeBotGlobal - Sistema de Logging
Configuração avançada de logging com rotação de arquivos e formatação personalizada
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class FormateadorPersonalizado(logging.Formatter):
    """Formatador personalizado com cores e emojis para diferentes níveis"""
    
    # Cores ANSI para terminal
    CORES = {
        'DEBUG': '\033[36m',     # Ciano
        'INFO': '\033[32m',      # Verde
        'WARNING': '\033[33m',   # Amarelo
        'ERROR': '\033[31m',     # Vermelho
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    # Emojis para diferentes níveis
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def __init__(self, usar_cores: bool = True, usar_emojis: bool = True):
        """
        Inicializa o formatador personalizado
        
        Args:
            usar_cores: Se deve usar cores no terminal
            usar_emojis: Se deve usar emojis nos logs
        """
        self.usar_cores = usar_cores
        self.usar_emojis = usar_emojis
        
        # Formato base
        formato_base = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        super().__init__(formato_base, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record):
        """Formata o registro de log"""
        # Obter formatação base
        log_formatado = super().format(record)
        
        # Adicionar emoji se habilitado
        if self.usar_emojis:
            emoji = self.EMOJIS.get(record.levelname, '')
            if emoji:
                log_formatado = f"{emoji} {log_formatado}"
        
        # Adicionar cores se habilitado e estiver no terminal
        if self.usar_cores and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            cor = self.CORES.get(record.levelname, '')
            reset = self.CORES['RESET']
            log_formatado = f"{cor}{log_formatado}{reset}"
        
        return log_formatado


class FiltroNivel(logging.Filter):
    """Filtro para permitir apenas determinados níveis de log"""
    
    def __init__(self, nivel_minimo: int = logging.INFO):
        """
        Inicializa o filtro
        
        Args:
            nivel_minimo: Nível mínimo de log a ser permitido
        """
        super().__init__()
        self.nivel_minimo = nivel_minimo
    
    def filter(self, record):
        """Filtra registros baseado no nível"""
        return record.levelno >= self.nivel_minimo


def configurar_logger(
    nivel: str = 'INFO',
    arquivo_log: str = 'logs/trading.log',
    rotacao: bool = True,
    tamanho_max_mb: int = 10,
    backup_count: int = 5,
    formato_console: bool = True,
    formato_arquivo: bool = False
) -> logging.Logger:
    """
    Configura o sistema de logging do CryptoTradeBotGlobal
    
    Args:
        nivel: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        arquivo_log: Caminho para o arquivo de log
        rotacao: Se deve usar rotação de arquivos
        tamanho_max_mb: Tamanho máximo do arquivo em MB
        backup_count: Número de arquivos de backup
        formato_console: Se deve usar formatação especial no console
        formato_arquivo: Se deve usar formatação especial no arquivo
        
    Returns:
        Logger configurado
    """
    # Converter nível string para constante
    nivel_numerico = getattr(logging, nivel.upper(), logging.INFO)
    
    # Criar diretório de logs se não existir
    caminho_arquivo = Path(arquivo_log)
    caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar logger raiz
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(nivel_numerico)
    
    # Limpar handlers existentes
    for handler in logger_raiz.handlers[:]:
        logger_raiz.removeHandler(handler)
    
    # Configurar handler para console
    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setLevel(nivel_numerico)
    
    if formato_console:
        formatador_console = FormateadorPersonalizado(usar_cores=True, usar_emojis=True)
    else:
        formatador_console = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler_console.setFormatter(formatador_console)
    logger_raiz.addHandler(handler_console)
    
    # Configurar handler para arquivo
    if rotacao:
        # Usar rotação de arquivos
        handler_arquivo = logging.handlers.RotatingFileHandler(
            arquivo_log,
            maxBytes=tamanho_max_mb * 1024 * 1024,  # Converter MB para bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        # Arquivo simples
        handler_arquivo = logging.FileHandler(arquivo_log, encoding='utf-8')
    
    handler_arquivo.setLevel(nivel_numerico)
    
    if formato_arquivo:
        formatador_arquivo = FormateadorPersonalizado(usar_cores=False, usar_emojis=True)
    else:
        formatador_arquivo = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler_arquivo.setFormatter(formatador_arquivo)
    logger_raiz.addHandler(handler_arquivo)
    
    # Configurar loggers específicos
    configurar_loggers_especificos(nivel_numerico)
    
    # Log inicial
    logger = logging.getLogger(__name__)
    logger.info("📝 Sistema de logging configurado com sucesso")
    logger.info(f"📊 Nível: {nivel} | Arquivo: {arquivo_log} | Rotação: {rotacao}")
    
    return logger_raiz


def configurar_loggers_especificos(nivel: int):
    """
    Configura loggers específicos para diferentes módulos
    
    Args:
        nivel: Nível de logging a ser aplicado
    """
    # Configurações específicas por módulo
    configuracoes_modulos = {
        'aiohttp': logging.WARNING,      # Reduzir logs do aiohttp
        'websockets': logging.WARNING,   # Reduzir logs do websockets
        'ccxt': logging.INFO,           # Manter logs do CCXT
        'urllib3': logging.WARNING,      # Reduzir logs do urllib3
        'requests': logging.WARNING,     # Reduzir logs do requests
    }
    
    for modulo, nivel_modulo in configuracoes_modulos.items():
        logger_modulo = logging.getLogger(modulo)
        logger_modulo.setLevel(nivel_modulo)


def obter_logger(nome: str) -> logging.Logger:
    """
    Obtém um logger específico para um módulo
    
    Args:
        nome: Nome do módulo/logger
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(nome)


def log_performance(func):
    """
    Decorator para medir e logar performance de funções
    
    Args:
        func: Função a ser decorada
        
    Returns:
        Função decorada
    """
    import time
    import functools
    
    @functools.wraps(func)
    async def wrapper_async(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        inicio = time.time()
        
        try:
            resultado = await func(*args, **kwargs)
            duracao = time.time() - inicio
            logger.debug(f"⏱️ {func.__name__} executada em {duracao:.3f}s")
            return resultado
        except Exception as e:
            duracao = time.time() - inicio
            logger.error(f"❌ {func.__name__} falhou após {duracao:.3f}s: {str(e)}")
            raise
    
    @functools.wraps(func)
    def wrapper_sync(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        inicio = time.time()
        
        try:
            resultado = func(*args, **kwargs)
            duracao = time.time() - inicio
            logger.debug(f"⏱️ {func.__name__} executada em {duracao:.3f}s")
            return resultado
        except Exception as e:
            duracao = time.time() - inicio
            logger.error(f"❌ {func.__name__} falhou após {duracao:.3f}s: {str(e)}")
            raise
    
    # Verificar se é função async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return wrapper_async
    else:
        return wrapper_sync


def log_entrada_saida(func):
    """
    Decorator para logar entrada e saída de funções
    
    Args:
        func: Função a ser decorada
        
    Returns:
        Função decorada
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper_async(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"🔄 Entrando em {func.__name__}")
        
        try:
            resultado = await func(*args, **kwargs)
            logger.debug(f"✅ Saindo de {func.__name__}")
            return resultado
        except Exception as e:
            logger.debug(f"❌ Erro em {func.__name__}: {str(e)}")
            raise
    
    @functools.wraps(func)
    def wrapper_sync(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"🔄 Entrando em {func.__name__}")
        
        try:
            resultado = func(*args, **kwargs)
            logger.debug(f"✅ Saindo de {func.__name__}")
            return resultado
        except Exception as e:
            logger.debug(f"❌ Erro em {func.__name__}: {str(e)}")
            raise
    
    # Verificar se é função async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return wrapper_async
    else:
        return wrapper_sync


class GerenciadorContextoLog:
    """Gerenciador de contexto para logging estruturado"""
    
    def __init__(self, logger: logging.Logger, mensagem: str, nivel: int = logging.INFO):
        """
        Inicializa o gerenciador de contexto
        
        Args:
            logger: Logger a ser usado
            mensagem: Mensagem base
            nivel: Nível de log
        """
        self.logger = logger
        self.mensagem = mensagem
        self.nivel = nivel
        self.inicio = None
    
    def __enter__(self):
        """Entrada do contexto"""
        import time
        self.inicio = time.time()
        self.logger.log(self.nivel, f"🔄 Iniciando: {self.mensagem}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Saída do contexto"""
        import time
        duracao = time.time() - self.inicio if self.inicio else 0
        
        if exc_type is None:
            self.logger.log(self.nivel, f"✅ Concluído: {self.mensagem} ({duracao:.3f}s)")
        else:
            self.logger.error(f"❌ Erro em: {self.mensagem} ({duracao:.3f}s) - {exc_val}")


def criar_arquivo_log_diario(diretorio: str = 'logs') -> str:
    """
    Cria nome de arquivo de log baseado na data atual
    
    Args:
        diretorio: Diretório onde criar o arquivo
        
    Returns:
        Caminho completo do arquivo de log
    """
    hoje = datetime.now().strftime('%Y-%m-%d')
    nome_arquivo = f"trading_{hoje}.log"
    
    caminho_diretorio = Path(diretorio)
    caminho_diretorio.mkdir(exist_ok=True)
    
    return str(caminho_diretorio / nome_arquivo)


def limpar_logs_antigos(diretorio: str = 'logs', dias_manter: int = 30):
    """
    Remove arquivos de log mais antigos que o número especificado de dias
    
    Args:
        diretorio: Diretório dos logs
        dias_manter: Número de dias para manter os logs
    """
    import time
    
    logger = logging.getLogger(__name__)
    caminho_diretorio = Path(diretorio)
    
    if not caminho_diretorio.exists():
        return
    
    tempo_limite = time.time() - (dias_manter * 24 * 60 * 60)
    arquivos_removidos = 0
    
    for arquivo in caminho_diretorio.glob('*.log*'):
        if arquivo.stat().st_mtime < tempo_limite:
            try:
                arquivo.unlink()
                arquivos_removidos += 1
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível remover {arquivo}: {e}")
    
    if arquivos_removidos > 0:
        logger.info(f"🧹 Removidos {arquivos_removidos} arquivos de log antigos")


if __name__ == "__main__":
    # Teste do sistema de logging
    configurar_logger(nivel='DEBUG')
    
    logger = obter_logger(__name__)
    
    # Testar diferentes níveis
    logger.debug("🔍 Mensagem de debug")
    logger.info("ℹ️ Mensagem informativa")
    logger.warning("⚠️ Mensagem de aviso")
    logger.error("❌ Mensagem de erro")
    logger.critical("🚨 Mensagem crítica")
    
    # Testar contexto
    with GerenciadorContextoLog(logger, "Teste de operação"):
        import time
        time.sleep(1)
    
    print("✅ Teste do sistema de logging concluído!")
