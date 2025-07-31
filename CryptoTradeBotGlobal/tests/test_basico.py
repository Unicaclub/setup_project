"""
CryptoTradeBotGlobal - Testes Básicos
Testes fundamentais para verificar funcionamento do sistema
"""

import pytest
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Adicionar src ao path para importações
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import CarregarConfiguracoes, validar_configuracoes, ConfiguracaoExchange, ConfiguracaoRisco
from src.utils.logger import configurar_logger, obter_logger
from src.core.bot_trading import BotTrading, GerenciadorRiscoSimplificado, AdaptadorExchangeSimulado


class TestConfiguracoes:
    """Testes para o sistema de configurações"""
    
    def test_carregar_configuracoes_padrao(self):
        """Testa carregamento de configurações padrão"""
        config = CarregarConfiguracoes()
        
        # Verificar se configurações básicas existem
        assert config is not None
        assert config.risco is not None
        assert config.trading is not None
        assert config.sistema is not None
        
        # Verificar valores padrão
        assert config.risco.tamanho_maximo_posicao_pct == 5.0
        assert config.risco.stop_loss_pct == 2.0
        assert config.risco.take_profit_pct == 6.0
        assert config.trading.modo_simulacao is True
        
    def test_configuracao_exchange(self):
        """Testa criação de configuração de exchange"""
        config_exchange = ConfiguracaoExchange(
            nome="teste",
            chave_api="chave_teste",
            chave_secreta="secreta_teste",
            sandbox=True
        )
        
        assert config_exchange.nome == "teste"
        assert config_exchange.chave_api == "chave_teste"
        assert config_exchange.sandbox is True
        assert config_exchange.ativo is True
        
    def test_configuracao_risco(self):
        """Testa configuração de risco"""
        config_risco = ConfiguracaoRisco(
            tamanho_maximo_posicao_pct=10.0,
            stop_loss_pct=3.0,
            take_profit_pct=9.0
        )
        
        assert config_risco.tamanho_maximo_posicao_pct == 10.0
        assert config_risco.stop_loss_pct == 3.0
        assert config_risco.take_profit_pct == 9.0
        
    def test_validacao_configuracoes_sem_exchanges(self):
        """Testa validação com configurações sem exchanges"""
        config = CarregarConfiguracoes()
        
        # Remover todos os exchanges para testar validação
        config.exchanges = {}
        
        # Deve falhar na validação
        assert validar_configuracoes(config) is False


class TestSistemaLogging:
    """Testes para o sistema de logging"""
    
    def test_configurar_logger(self):
        """Testa configuração do sistema de logging"""
        logger = configurar_logger(nivel='DEBUG')
        
        assert logger is not None
        
        # Testar obtenção de logger específico
        logger_teste = obter_logger('teste')
        assert logger_teste is not None
        
    def test_niveis_logging(self):
        """Testa diferentes níveis de logging"""
        configurar_logger(nivel='DEBUG')
        logger = obter_logger(__name__)
        
        # Testar diferentes níveis (não deve gerar erro)
        logger.debug("Mensagem de debug")
        logger.info("Mensagem informativa")
        logger.warning("Mensagem de aviso")
        logger.error("Mensagem de erro")
        logger.critical("Mensagem crítica")


class TestGerenciadorRisco:
    """Testes para o gerenciador de risco"""
    
    @pytest.fixture
    def configuracoes_teste(self):
        """Fixture com configurações de teste"""
        config = CarregarConfiguracoes()
        config.risco.tamanho_maximo_posicao_pct = 10.0
        config.risco.posicoes_maximas_abertas = 3
        config.risco.perdas_consecutivas_max = 2
        return config
    
    @pytest.fixture
    def gerenciador_risco(self, configuracoes_teste):
        """Fixture com gerenciador de risco"""
        return GerenciadorRiscoSimplificado(configuracoes_teste)
    
    @pytest.mark.asyncio
    async def test_validar_ordem_valida(self, gerenciador_risco):
        """Testa validação de ordem válida"""
        valida, motivo, quantidade = await gerenciador_risco.validar_ordem(
            simbolo="BTC/USDT",
            lado="BUY",
            quantidade=Decimal('0.01'),
            preco=Decimal('50000')
        )
        
        assert valida is True
        assert "válida" in motivo.lower()
        assert quantidade == Decimal('0.01')
    
    @pytest.mark.asyncio
    async def test_validar_ordem_posicao_grande(self, gerenciador_risco):
        """Testa validação com posição muito grande"""
        valida, motivo, quantidade_ajustada = await gerenciador_risco.validar_ordem(
            simbolo="BTC/USDT",
            lado="BUY",
            quantidade=Decimal('1.0'),  # Muito grande
            preco=Decimal('50000')
        )
        
        # Deve ajustar a quantidade
        assert valida is True
        assert "ajustada" in motivo.lower()
        assert quantidade_ajustada < Decimal('1.0')
    
    @pytest.mark.asyncio
    async def test_calcular_stop_loss_take_profit(self, gerenciador_risco):
        """Testa cálculo de stop loss e take profit"""
        preco_entrada = Decimal('50000')
        
        # Teste para ordem de compra
        stop_loss, take_profit = await gerenciador_risco.calcular_stop_loss_take_profit(
            lado="BUY",
            preco_entrada=preco_entrada
        )
        
        assert stop_loss < preco_entrada  # Stop loss deve ser menor
        assert take_profit > preco_entrada  # Take profit deve ser maior
        
        # Verificar percentuais aproximados
        perda_pct = ((preco_entrada - stop_loss) / preco_entrada) * 100
        ganho_pct = ((take_profit - preco_entrada) / preco_entrada) * 100
        
        assert abs(perda_pct - 2.0) < 0.1  # Aproximadamente 2%
        assert abs(ganho_pct - 6.0) < 0.1  # Aproximadamente 6%
    
    @pytest.mark.asyncio
    async def test_atualizar_posicao(self, gerenciador_risco):
        """Testa atualização de posição"""
        simbolo = "BTC/USDT"
        quantidade = Decimal('0.01')
        preco = Decimal('50000')
        
        # Adicionar posição
        await gerenciador_risco.atualizar_posicao(simbolo, quantidade, preco, "BUY")
        
        assert simbolo in gerenciador_risco.posicoes_abertas
        posicao = gerenciador_risco.posicoes_abertas[simbolo]
        assert posicao['quantidade'] == quantidade
        assert posicao['preco_medio'] == preco
    
    @pytest.mark.asyncio
    async def test_atualizar_metricas(self, gerenciador_risco):
        """Testa atualização de métricas"""
        valor_inicial = gerenciador_risco.valor_inicial
        novo_valor = valor_inicial * Decimal('1.1')  # +10%
        
        await gerenciador_risco.atualizar_metricas(novo_valor)
        
        assert gerenciador_risco.valor_atual == novo_valor
        assert gerenciador_risco.valor_maximo == novo_valor
        assert gerenciador_risco.drawdown_atual == 0.0  # Sem drawdown


class TestAdaptadorExchange:
    """Testes para o adaptador de exchange simulado"""
    
    @pytest.fixture
    def config_exchange(self):
        """Fixture com configuração de exchange"""
        return ConfiguracaoExchange(
            nome="teste",
            chave_api="chave_teste",
            chave_secreta="secreta_teste",
            sandbox=True
        )
    
    @pytest.fixture
    def adaptador(self, config_exchange):
        """Fixture com adaptador de exchange"""
        return AdaptadorExchangeSimulado("teste", config_exchange)
    
    @pytest.mark.asyncio
    async def test_conectar_desconectar(self, adaptador):
        """Testa conexão e desconexão"""
        # Testar conexão
        resultado = await adaptador.conectar()
        assert resultado is True
        assert adaptador.conectado is True
        
        # Testar desconexão
        await adaptador.desconectar()
        assert adaptador.conectado is False
    
    @pytest.mark.asyncio
    async def test_obter_ticker(self, adaptador):
        """Testa obtenção de ticker"""
        await adaptador.conectar()
        
        ticker = await adaptador.obter_ticker("BTC/USDT")
        
        assert ticker is not None
        assert 'simbolo' in ticker
        assert 'preco' in ticker
        assert 'bid' in ticker
        assert 'ask' in ticker
        assert ticker['simbolo'] == "BTC/USDT"
        assert ticker['preco'] > 0
    
    @pytest.mark.asyncio
    async def test_obter_saldos(self, adaptador):
        """Testa obtenção de saldos"""
        await adaptador.conectar()
        
        saldos = await adaptador.obter_saldos()
        
        assert saldos is not None
        assert isinstance(saldos, dict)
        assert 'USDT' in saldos
        assert saldos['USDT'] > 0
    
    @pytest.mark.asyncio
    async def test_colocar_ordem_simulada(self, adaptador):
        """Testa colocação de ordem simulada"""
        await adaptador.conectar()
        
        # Ordem de compra
        ordem = await adaptador.colocar_ordem_simulada(
            simbolo="BTC/USDT",
            lado="BUY",
            quantidade=Decimal('0.001'),
            preco=Decimal('50000')
        )
        
        assert ordem is not None
        assert 'id_ordem' in ordem
        assert ordem['simbolo'] == "BTC/USDT"
        assert ordem['lado'] == "BUY"
        assert ordem['status'] == "EXECUTADA"
    
    @pytest.mark.asyncio
    async def test_ticker_simbolo_inexistente(self, adaptador):
        """Testa ticker para símbolo inexistente"""
        await adaptador.conectar()
        
        with pytest.raises(Exception):
            await adaptador.obter_ticker("SIMBOLO/INEXISTENTE")


class TestBotTrading:
    """Testes para o bot de trading principal"""
    
    @pytest.fixture
    def configuracoes_bot(self):
        """Fixture com configurações para o bot"""
        config = CarregarConfiguracoes()
        
        # Adicionar exchange fictício para teste
        config.exchanges['teste'] = ConfiguracaoExchange(
            nome="teste",
            chave_api="chave_teste",
            chave_secreta="secreta_teste",
            sandbox=True,
            ativo=True
        )
        
        return config
    
    @pytest.fixture
    def bot_trading(self, configuracoes_bot):
        """Fixture com bot de trading"""
        return BotTrading(configuracoes_bot)
    
    @pytest.mark.asyncio
    async def test_inicializar_bot(self, bot_trading):
        """Testa inicialização do bot"""
        assert bot_trading is not None
        assert bot_trading.config is not None
        assert bot_trading.gerenciador_risco is not None
        assert bot_trading.ciclos_executados == 0
        assert bot_trading.trades_executados == 0
    
    @pytest.mark.asyncio
    async def test_conectar_exchanges(self, bot_trading):
        """Testa conexão com exchanges"""
        resultado = await bot_trading.conectar_exchanges()
        
        assert resultado is True
        assert len(bot_trading.exchanges) > 0
        
        # Verificar se pelo menos um exchange está conectado
        conectados = [ex.conectado for ex in bot_trading.exchanges.values()]
        assert any(conectados)
    
    @pytest.mark.asyncio
    async def test_inicializar_gerenciamento_risco(self, bot_trading):
        """Testa inicialização do gerenciamento de risco"""
        # Não deve gerar erro
        await bot_trading.inicializar_gerenciamento_risco()
    
    @pytest.mark.asyncio
    async def test_finalizar_bot(self, bot_trading):
        """Testa finalização do bot"""
        # Conectar primeiro
        await bot_trading.conectar_exchanges()
        
        # Finalizar
        await bot_trading.finalizar()
        
        # Verificar se todos os exchanges foram desconectados
        for exchange in bot_trading.exchanges.values():
            assert exchange.conectado is False


class TestIntegracao:
    """Testes de integração do sistema completo"""
    
    @pytest.mark.asyncio
    async def test_fluxo_completo_basico(self):
        """Testa fluxo completo básico do sistema"""
        # Configurar logging
        configurar_logger(nivel='INFO')
        
        # Carregar configurações
        config = CarregarConfiguracoes()
        
        # Adicionar exchange de teste
        config.exchanges['teste'] = ConfiguracaoExchange(
            nome="teste",
            chave_api="chave_teste_completa",
            chave_secreta="secreta_teste_completa",
            sandbox=True,
            ativo=True
        )
        
        # Validar configurações
        assert validar_configuracoes(config) is True
        
        # Criar bot
        bot = BotTrading(config)
        
        # Conectar exchanges
        conectado = await bot.conectar_exchanges()
        assert conectado is True
        
        # Inicializar gerenciamento de risco
        await bot.inicializar_gerenciamento_risco()
        
        # Executar um ciclo de trading (deve funcionar sem erro)
        await bot.executar_ciclo_trading()
        
        # Verificar se ciclo foi executado
        assert bot.ciclos_executados == 1
        assert bot.ultima_execucao is not None
        
        # Finalizar
        await bot.finalizar()


def test_importacoes_basicas():
    """Testa se todas as importações básicas funcionam"""
    # Testar importações principais
    from config import CarregarConfiguracoes
    from src.utils.logger import configurar_logger
    from src.core.bot_trading import BotTrading
    
    # Se chegou até aqui, as importações funcionaram
    assert True


def test_estrutura_diretorios():
    """Testa se a estrutura de diretórios está correta"""
    projeto_root = Path(__file__).parent.parent
    
    # Verificar diretórios principais
    assert (projeto_root / "src").exists()
    assert (projeto_root / "src" / "core").exists()
    assert (projeto_root / "src" / "utils").exists()
    assert (projeto_root / "tests").exists()
    assert (projeto_root / "config").exists()
    
    # Verificar arquivos principais
    assert (projeto_root / "main.py").exists()
    assert (projeto_root / "config.py").exists()
    assert (projeto_root / "requirements.txt").exists()


if __name__ == "__main__":
    # Executar testes básicos se chamado diretamente
    print("🧪 Executando testes básicos...")
    
    try:
        # Teste simples de importações
        test_importacoes_basicas()
        print("✅ Importações básicas: OK")
        
        # Teste de estrutura
        test_estrutura_diretorios()
        print("✅ Estrutura de diretórios: OK")
        
        # Teste de configurações
        test_config = TestConfiguracoes()
        test_config.test_carregar_configuracoes_padrao()
        print("✅ Configurações básicas: OK")
        
        # Teste de logging
        test_log = TestSistemaLogging()
        test_log.test_configurar_logger()
        print("✅ Sistema de logging: OK")
        
        print("\n🎉 Todos os testes básicos passaram!")
        print("📋 Para executar testes completos, use: pytest tests/")
        
    except Exception as e:
        print(f"❌ Erro nos testes básicos: {str(e)}")
        sys.exit(1)
