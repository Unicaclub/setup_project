"""
CryptoTradeBotGlobal - Sistema de Configuração
Gerenciamento centralizado de configurações e variáveis de ambiente
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class ConfiguracaoExchange:
    """Configuração para um exchange específico"""
    nome: str
    chave_api: str
    chave_secreta: str
    sandbox: bool = True
    ativo: bool = True
    limite_requisicoes: int = 10
    timeout: int = 30


@dataclass
class ConfiguracaoRisco:
    """Configurações de gerenciamento de risco"""
    tamanho_maximo_posicao_pct: float = 5.0
    perda_maxima_diaria_pct: float = 3.0
    drawdown_maximo_pct: float = 10.0
    posicoes_maximas_abertas: int = 5
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 6.0
    ratio_risco_recompensa_min: float = 2.0
    perdas_consecutivas_max: int = 3


@dataclass
class ConfiguracaoTrading:
    """Configurações de trading"""
    pares_moedas: list = field(default_factory=lambda: ['BTC/USDT', 'ETH/USDT'])
    intervalo_verificacao: int = 30  # segundos
    valor_inicial_portfolio: float = 10000.0
    modo_simulacao: bool = True
    estrategia_padrao: str = 'conservadora'


@dataclass
class ConfiguracaoSistema:
    """Configurações gerais do sistema"""
    nivel_log: str = 'INFO'
    arquivo_log: str = 'logs/trading.log'
    rotacao_log: bool = True
    tamanho_max_log_mb: int = 10
    backup_logs: int = 5
    timezone: str = 'America/Sao_Paulo'


@dataclass
class ConfiguracoesGlobais:
    """Configurações globais do sistema"""
    exchanges: Dict[str, ConfiguracaoExchange] = field(default_factory=dict)
    risco: ConfiguracaoRisco = field(default_factory=ConfiguracaoRisco)
    trading: ConfiguracaoTrading = field(default_factory=ConfiguracaoTrading)
    sistema: ConfiguracaoSistema = field(default_factory=ConfiguracaoSistema)
    
    def obter_exchange(self, nome: str) -> Optional[ConfiguracaoExchange]:
        """Obtém configuração de um exchange específico"""
        return self.exchanges.get(nome)
    
    def listar_exchanges_ativos(self) -> Dict[str, ConfiguracaoExchange]:
        """Lista apenas exchanges ativos"""
        return {nome: config for nome, config in self.exchanges.items() if config.ativo}


def CarregarConfiguracoes() -> ConfiguracoesGlobais:
    """
    Carrega todas as configurações do sistema
    
    Returns:
        Objeto com todas as configurações
    """
    # Carregar variáveis de ambiente
    arquivo_env = Path(__file__).parent / '.env'
    if arquivo_env.exists():
        load_dotenv(arquivo_env)
    
    logger = logging.getLogger(__name__)
    logger.info("📋 Carregando configurações do sistema...")
    
    # Configurações de sistema
    config_sistema = ConfiguracaoSistema(
        nivel_log=os.getenv('LOG_LEVEL', 'INFO'),
        arquivo_log=os.getenv('LOG_FILE', 'logs/trading.log'),
        rotacao_log=os.getenv('LOG_ROTATION', 'true').lower() == 'true',
        tamanho_max_log_mb=int(os.getenv('LOG_MAX_SIZE_MB', '10')),
        backup_logs=int(os.getenv('LOG_BACKUP_COUNT', '5')),
        timezone=os.getenv('TIMEZONE', 'America/Sao_Paulo')
    )
    
    # Configurações de risco
    config_risco = ConfiguracaoRisco(
        tamanho_maximo_posicao_pct=float(os.getenv('MAX_POSITION_SIZE_PCT', '5.0')),
        perda_maxima_diaria_pct=float(os.getenv('MAX_DAILY_LOSS_PCT', '3.0')),
        drawdown_maximo_pct=float(os.getenv('MAX_DRAWDOWN_PCT', '10.0')),
        posicoes_maximas_abertas=int(os.getenv('MAX_OPEN_POSITIONS', '5')),
        stop_loss_pct=float(os.getenv('STOP_LOSS_PCT', '2.0')),
        take_profit_pct=float(os.getenv('TAKE_PROFIT_PCT', '6.0')),
        ratio_risco_recompensa_min=float(os.getenv('MIN_RISK_REWARD_RATIO', '2.0')),
        perdas_consecutivas_max=int(os.getenv('MAX_CONSECUTIVE_LOSSES', '3'))
    )
    
    # Configurações de trading
    pares_env = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT')
    pares_lista = [par.strip() for par in pares_env.split(',')]
    
    config_trading = ConfiguracaoTrading(
        pares_moedas=pares_lista,
        intervalo_verificacao=int(os.getenv('CHECK_INTERVAL', '30')),
        valor_inicial_portfolio=float(os.getenv('INITIAL_PORTFOLIO_VALUE', '10000.0')),
        modo_simulacao=os.getenv('SIMULATION_MODE', 'true').lower() == 'true',
        estrategia_padrao=os.getenv('DEFAULT_STRATEGY', 'conservadora')
    )
    
    # Configurações de exchanges
    exchanges = {}
    
    # Binance
    if os.getenv('BINANCE_API_KEY') and os.getenv('BINANCE_API_SECRET'):
        exchanges['binance'] = ConfiguracaoExchange(
            nome='binance',
            chave_api=os.getenv('BINANCE_API_KEY'),
            chave_secreta=os.getenv('BINANCE_API_SECRET'),
            sandbox=os.getenv('BINANCE_TESTNET', 'true').lower() == 'true',
            ativo=os.getenv('BINANCE_ENABLED', 'true').lower() == 'true',
            limite_requisicoes=int(os.getenv('BINANCE_RATE_LIMIT', '10')),
            timeout=int(os.getenv('BINANCE_TIMEOUT', '30'))
        )
    
    # Coinbase Pro
    if os.getenv('COINBASE_API_KEY') and os.getenv('COINBASE_API_SECRET'):
        exchanges['coinbase'] = ConfiguracaoExchange(
            nome='coinbase',
            chave_api=os.getenv('COINBASE_API_KEY'),
            chave_secreta=os.getenv('COINBASE_API_SECRET'),
            sandbox=os.getenv('COINBASE_SANDBOX', 'true').lower() == 'true',
            ativo=os.getenv('COINBASE_ENABLED', 'true').lower() == 'true',
            limite_requisicoes=int(os.getenv('COINBASE_RATE_LIMIT', '5')),
            timeout=int(os.getenv('COINBASE_TIMEOUT', '30'))
        )
    
    # Kraken
    if os.getenv('KRAKEN_API_KEY') and os.getenv('KRAKEN_API_SECRET'):
        exchanges['kraken'] = ConfiguracaoExchange(
            nome='kraken',
            chave_api=os.getenv('KRAKEN_API_KEY'),
            chave_secreta=os.getenv('KRAKEN_API_SECRET'),
            sandbox=False,  # Kraken não tem sandbox
            ativo=os.getenv('KRAKEN_ENABLED', 'true').lower() == 'true',
            limite_requisicoes=int(os.getenv('KRAKEN_RATE_LIMIT', '2')),
            timeout=int(os.getenv('KRAKEN_TIMEOUT', '30'))
        )
    
    # Criar configurações globais
    configuracoes = ConfiguracoesGlobais(
        exchanges=exchanges,
        risco=config_risco,
        trading=config_trading,
        sistema=config_sistema
    )
    
    logger.info(f"✅ Configurações carregadas: {len(exchanges)} exchanges configurados")
    
    return configuracoes


def validar_configuracoes(config: ConfiguracoesGlobais) -> bool:
    """
    Valida se as configurações estão corretas
    
    Args:
        config: Configurações a serem validadas
        
    Returns:
        True se válidas
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Validar se há pelo menos um exchange configurado
        if not config.exchanges:
            logger.error("❌ Nenhum exchange configurado!")
            return False
        
        # Validar se há pelo menos um exchange ativo
        exchanges_ativos = config.listar_exchanges_ativos()
        if not exchanges_ativos:
            logger.error("❌ Nenhum exchange ativo!")
            return False
        
        # Validar configurações de risco
        if config.risco.tamanho_maximo_posicao_pct <= 0 or config.risco.tamanho_maximo_posicao_pct > 100:
            logger.error("❌ Tamanho máximo de posição inválido!")
            return False
        
        if config.risco.perda_maxima_diaria_pct <= 0 or config.risco.perda_maxima_diaria_pct > 50:
            logger.error("❌ Perda máxima diária inválida!")
            return False
        
        if config.risco.stop_loss_pct <= 0 or config.risco.stop_loss_pct > 20:
            logger.error("❌ Stop loss inválido!")
            return False
        
        if config.risco.take_profit_pct <= config.risco.stop_loss_pct:
            logger.error("❌ Take profit deve ser maior que stop loss!")
            return False
        
        # Validar configurações de trading
        if not config.trading.pares_moedas:
            logger.error("❌ Nenhum par de moedas configurado!")
            return False
        
        if config.trading.intervalo_verificacao < 10:
            logger.error("❌ Intervalo de verificação muito baixo!")
            return False
        
        if config.trading.valor_inicial_portfolio <= 0:
            logger.error("❌ Valor inicial do portfólio inválido!")
            return False
        
        # Validar chaves de API
        for nome, exchange_config in exchanges_ativos.items():
            if not exchange_config.chave_api or not exchange_config.chave_secreta:
                logger.error(f"❌ Chaves de API não configuradas para {nome}!")
                return False
            
            if len(exchange_config.chave_api) < 10:
                logger.error(f"❌ Chave API muito curta para {nome}!")
                return False
        
        logger.info("✅ Todas as configurações são válidas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação das configurações: {str(e)}")
        return False


def obter_configuracao_exchange(nome_exchange: str) -> Optional[ConfiguracaoExchange]:
    """
    Obtém configuração específica de um exchange
    
    Args:
        nome_exchange: Nome do exchange
        
    Returns:
        Configuração do exchange ou None
    """
    configuracoes = CarregarConfiguracoes()
    return configuracoes.obter_exchange(nome_exchange)


def criar_diretorios_necessarios():
    """Cria diretórios necessários para o funcionamento do sistema"""
    diretorios = [
        'logs',
        'data',
        'backups',
        'temp'
    ]
    
    for diretorio in diretorios:
        caminho = Path(__file__).parent / diretorio
        caminho.mkdir(exist_ok=True)


def exibir_resumo_configuracoes(config: ConfiguracoesGlobais):
    """
    Exibe um resumo das configurações carregadas
    
    Args:
        config: Configurações do sistema
    """
    print("\n" + "=" * 60)
    print("📋 RESUMO DAS CONFIGURAÇÕES")
    print("=" * 60)
    
    print(f"🏦 Exchanges configurados: {len(config.exchanges)}")
    for nome, exchange_config in config.exchanges.items():
        status = "✅ ATIVO" if exchange_config.ativo else "❌ INATIVO"
        sandbox = "🧪 SANDBOX" if exchange_config.sandbox else "🚀 PRODUÇÃO"
        print(f"  • {nome.upper()}: {status} ({sandbox})")
    
    print(f"\n🛡️ Configurações de Risco:")
    print(f"  • Tamanho máximo posição: {config.risco.tamanho_maximo_posicao_pct}%")
    print(f"  • Perda máxima diária: {config.risco.perda_maxima_diaria_pct}%")
    print(f"  • Stop Loss: {config.risco.stop_loss_pct}%")
    print(f"  • Take Profit: {config.risco.take_profit_pct}%")
    
    print(f"\n📈 Configurações de Trading:")
    print(f"  • Pares: {', '.join(config.trading.pares_moedas)}")
    print(f"  • Intervalo: {config.trading.intervalo_verificacao}s")
    print(f"  • Modo: {'🧪 SIMULAÇÃO' if config.trading.modo_simulacao else '🚀 REAL'}")
    
    print("=" * 60)


# Configuração básica para modo teste
CONFIGURACAO_BASICA = {
    'nome_sistema': 'CryptoTradeBotGlobal',
    'versao': '1.0.0',
    'autor': 'CryptoTradeBotGlobal Team',
    'descricao': 'Sistema de Trading de Criptomoedas em Português Brasileiro',
    'ambiente': 'desenvolvimento',
    'modo_debug': True,
    'suporte_simulacao': True,
    'exchanges_suportados': ['binance', 'coinbase', 'kraken', 'okx'],
    'pares_padrao': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
    'configuracao_minima': {
        'valor_inicial': 10000.0,
        'risco_maximo': 5.0,
        'stop_loss': 2.0,
        'take_profit': 4.0
    }
}


if __name__ == "__main__":
    # Teste das configurações
    try:
        criar_diretorios_necessarios()
        config = CarregarConfiguracoes()
        
        if validar_configuracoes(config):
            exibir_resumo_configuracoes(config)
            print("✅ Configurações válidas!")
        else:
            print("❌ Configurações inválidas!")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
