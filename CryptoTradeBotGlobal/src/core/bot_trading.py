"""
CryptoTradeBotGlobal - Bot de Trading Principal
Classe principal que coordena todas as operações de trading
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
import time

from src.utils.logger import obter_logger, log_performance, GerenciadorContextoLog
from config import ConfiguracoesGlobais, ConfiguracaoExchange


class GerenciadorRiscoSimplificado:
    """Gerenciador de risco simplificado para o bot"""
    
    def __init__(self, configuracoes: ConfiguracoesGlobais):
        """
        Inicializa o gerenciador de risco
        
        Args:
            configuracoes: Configurações globais do sistema
        """
        self.config = configuracoes.risco
        self.logger = obter_logger(__name__)
        
        # Estado do portfólio
        self.valor_inicial = Decimal(str(configuracoes.trading.valor_inicial_portfolio))
        self.valor_atual = self.valor_inicial
        self.posicoes_abertas = {}
        self.historico_trades = []
        self.perdas_consecutivas = 0
        
        # Métricas de risco
        self.drawdown_atual = 0.0
        self.valor_maximo = self.valor_inicial
        self.perda_diaria = 0.0
        self.inicio_dia = datetime.now().date()
        
    async def validar_ordem(self, simbolo: str, lado: str, quantidade: Decimal, preco: Decimal) -> tuple[bool, str, Decimal]:
        """
        Valida se uma ordem pode ser executada
        
        Args:
            simbolo: Par de moedas
            lado: BUY ou SELL
            quantidade: Quantidade da ordem
            preco: Preço da ordem
            
        Returns:
            (válida, motivo, quantidade_ajustada)
        """
        try:
            # Verificar se não excede o número máximo de posições
            if len(self.posicoes_abertas) >= self.config.posicoes_maximas_abertas:
                return False, "Número máximo de posições atingido", quantidade
            
            # Calcular valor da ordem
            valor_ordem = quantidade * preco
            
            # Verificar tamanho máximo da posição
            tamanho_max_posicao = (self.valor_atual * Decimal(str(self.config.tamanho_maximo_posicao_pct))) / Decimal('100')
            if valor_ordem > tamanho_max_posicao:
                # Ajustar quantidade
                quantidade_ajustada = tamanho_max_posicao / preco
                self.logger.warning(f"⚠️ Quantidade ajustada de {quantidade} para {quantidade_ajustada}")
                return True, "Quantidade ajustada por limite de posição", quantidade_ajustada
            
            # Verificar perdas consecutivas
            if self.perdas_consecutivas >= self.config.perdas_consecutivas_max:
                return False, "Muitas perdas consecutivas - período de cooling off", quantidade
            
            # Verificar perda diária
            if self.perda_diaria >= (self.valor_inicial * Decimal(str(self.config.perda_maxima_diaria_pct)) / Decimal('100')):
                return False, "Limite de perda diária atingido", quantidade
            
            # Verificar drawdown máximo
            if self.drawdown_atual >= self.config.drawdown_maximo_pct:
                return False, "Drawdown máximo atingido", quantidade
            
            return True, "Ordem válida", quantidade
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação da ordem: {str(e)}")
            return False, f"Erro na validação: {str(e)}", quantidade
    
    async def calcular_stop_loss_take_profit(self, lado: str, preco_entrada: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calcula stop loss e take profit para uma posição
        
        Args:
            lado: BUY ou SELL
            preco_entrada: Preço de entrada da posição
            
        Returns:
            (stop_loss, take_profit)
        """
        stop_loss_pct = Decimal(str(self.config.stop_loss_pct))
        take_profit_pct = Decimal(str(self.config.take_profit_pct))
        if lado.upper() == 'BUY':
            stop_loss = preco_entrada * (Decimal('1') - (stop_loss_pct / Decimal('100')))
            take_profit = preco_entrada * (Decimal('1') + (take_profit_pct / Decimal('100')))
        else:  # SELL
            stop_loss = preco_entrada * (Decimal('1') + (stop_loss_pct / Decimal('100')))
            take_profit = preco_entrada * (Decimal('1') - (take_profit_pct / Decimal('100')))
        
        return stop_loss, take_profit
    
    async def atualizar_posicao(self, simbolo: str, quantidade: Decimal, preco: Decimal, lado: str):
        """
        Atualiza uma posição no portfólio
        
        Args:
            simbolo: Par de moedas
            quantidade: Quantidade
            preco: Preço
            lado: BUY ou SELL
        """
        if simbolo not in self.posicoes_abertas:
            self.posicoes_abertas[simbolo] = {
                'quantidade': Decimal('0'),
                'preco_medio': Decimal('0'),
                'valor_total': Decimal('0'),
                'lado': lado,
                'timestamp': datetime.now()
            }
        
        posicao = self.posicoes_abertas[simbolo]
        
        if lado.upper() == 'BUY':
            # Adicionar à posição
            valor_anterior = posicao['valor_total']
            valor_novo = quantidade * preco
            
            posicao['quantidade'] += quantidade
            posicao['valor_total'] = valor_anterior + valor_novo
            posicao['preco_medio'] = posicao['valor_total'] / posicao['quantidade']
        else:
            # Reduzir posição (venda)
            posicao['quantidade'] -= quantidade
            if posicao['quantidade'] <= 0:
                # Posição fechada
                del self.posicoes_abertas[simbolo]
    
    async def atualizar_metricas(self, valor_portfolio: Decimal):
        """
        Atualiza métricas de risco do portfólio
        
        Args:
            valor_portfolio: Valor atual do portfólio
        """
        self.valor_atual = valor_portfolio
        
        # Atualizar valor máximo
        if valor_portfolio > self.valor_maximo:
            self.valor_maximo = valor_portfolio
        
        # Calcular drawdown
        self.drawdown_atual = ((self.valor_maximo - valor_portfolio) / self.valor_maximo) * 100
        
        # Verificar se é um novo dia
        hoje = datetime.now().date()
        if hoje != self.inicio_dia:
            self.perda_diaria = 0.0
            self.inicio_dia = hoje
        
        # Calcular perda diária
        if valor_portfolio < self.valor_inicial:
            self.perda_diaria = self.valor_inicial - valor_portfolio


class AdaptadorExchangeSimulado:
    """Adaptador simulado para testes sem conexão real"""
    
    def __init__(self, nome: str, config: ConfiguracaoExchange):
        """
        Inicializa o adaptador simulado
        
        Args:
            nome: Nome do exchange
            config: Configuração do exchange
        """
        self.nome = nome
        self.config = config
        self.logger = obter_logger(__name__)
        self.conectado = False
        
        # Preços simulados
        self.precos_simulados = {
            'BTC/USDT': Decimal('50000'),
            'ETH/USDT': Decimal('3000'),
            'BNB/USDT': Decimal('300'),
            'ADA/USDT': Decimal('0.50')
        }
        
        # Saldos simulados
        self.saldos_simulados = {
            'USDT': Decimal('10000'),
            'BTC': Decimal('0'),
            'ETH': Decimal('0'),
            'BNB': Decimal('0'),
            'ADA': Decimal('0')
        }
    
    async def conectar(self) -> bool:
        """Simula conexão com o exchange"""
        await asyncio.sleep(0.5)  # Simular latência
        self.conectado = True
        self.logger.info(f"🔗 Conectado ao {self.nome} (SIMULADO)")
        return True
    
    async def desconectar(self):
        """Simula desconexão do exchange"""
        self.conectado = False
        self.logger.info(f"🔌 Desconectado do {self.nome}")
    
    async def obter_ticker(self, simbolo: str) -> Dict[str, Any]:
        """
        Obtém ticker simulado
        
        Args:
            simbolo: Par de moedas
            
        Returns:
            Dados do ticker
        """
        if simbolo not in self.precos_simulados:
            raise Exception(f"Símbolo {simbolo} não suportado")
        
        preco_base = self.precos_simulados[simbolo]
        
        # Simular variação de preço (-1% a +1%)
        import random
        variacao = Decimal(str(random.uniform(-0.01, 0.01)))
        preco_atual = preco_base * (1 + variacao)
        
        # Atualizar preço simulado
        self.precos_simulados[simbolo] = preco_atual
        
        return {
            'simbolo': simbolo,
            'preco': preco_atual,
            'bid': preco_atual * Decimal('0.999'),
            'ask': preco_atual * Decimal('1.001'),
            'volume_24h': Decimal('1000'),
            'variacao_24h': variacao * 100,
            'timestamp': time.time()
        }
    
    async def obter_saldos(self) -> Dict[str, Decimal]:
        """Obtém saldos simulados"""
        return self.saldos_simulados.copy()
    
    async def colocar_ordem_simulada(self, simbolo: str, lado: str, quantidade: Decimal, preco: Decimal) -> Dict[str, Any]:
        """
        Simula colocação de ordem
        
        Args:
            simbolo: Par de moedas
            lado: BUY ou SELL
            quantidade: Quantidade
            preco: Preço
            
        Returns:
            Dados da ordem
        """
        # Simular execução da ordem
        import uuid
        ordem_id = str(uuid.uuid4())[:8]
        
        # Atualizar saldos simulados
        base_asset = simbolo.split('/')[0]
        quote_asset = simbolo.split('/')[1]
        
        if lado.upper() == 'BUY':
            # Comprar: reduzir quote asset, aumentar base asset
            custo_total = quantidade * preco
            if self.saldos_simulados.get(quote_asset, 0) >= custo_total:
                self.saldos_simulados[quote_asset] -= custo_total
                self.saldos_simulados[base_asset] = self.saldos_simulados.get(base_asset, Decimal('0')) + quantidade
            else:
                raise Exception("Saldo insuficiente")
        else:
            # Vender: reduzir base asset, aumentar quote asset
            if self.saldos_simulados.get(base_asset, 0) >= quantidade:
                self.saldos_simulados[base_asset] -= quantidade
                receita = quantidade * preco
                self.saldos_simulados[quote_asset] = self.saldos_simulados.get(quote_asset, Decimal('0')) + receita
            else:
                raise Exception("Saldo insuficiente")
        
        return {
            'id_ordem': ordem_id,
            'simbolo': simbolo,
            'lado': lado,
            'quantidade': quantidade,
            'preco': preco,
            'status': 'EXECUTADA',
            'timestamp': time.time()
        }


class BotTrading:
    """Classe principal do bot de trading"""
    
    def __init__(self, configuracoes: Optional[ConfiguracoesGlobais] = None):
        """
        Inicializa o bot de trading
        
        Args:
            configuracoes: Configurações globais do sistema (opcional para modo teste)
        """
        self.logger = obter_logger(__name__)
        
        # Se não há configurações, usar configurações básicas para teste
        if configuracoes is None:
            self.configuracao = self._criar_configuracoes_basicas()
        else:
            self.configuracao = configuracoes
        # Compatibilidade: garantir atributo 'config' para testes e código legado
        self.config = self.configuracao
        
        # Componentes principais
        self.gerenciador_risco = GerenciadorRiscoSimplificado(self.configuracao)
        self.exchanges: Dict[str, AdaptadorExchangeSimulado] = {}
        
        # Estado do bot
        self.ativo = False
        self.ciclos_executados = 0
        self.ultima_execucao = None
        
        # Estatísticas
        self.trades_executados = 0
        self.trades_lucrativos = 0
        self.valor_total_negociado = Decimal('0')
    
    def _criar_configuracoes_basicas(self) -> 'ConfiguracoesGlobais':
        """
        Cria configurações básicas para modo teste
        
        Returns:
            Configurações básicas
        """
        from config import CONFIGURACAO_BASICA
        
        # Criar uma configuração mínima para teste
        class ConfigBasica:
            def __init__(self):
                self.risco = type('obj', (object,), {
                    'posicoes_maximas_abertas': 3,
                    'tamanho_maximo_posicao_pct': 10,
                    'perdas_consecutivas_max': 3,
                    'perda_maxima_diaria_pct': 5,
                    'drawdown_maximo_pct': 15,
                    'stop_loss_pct': 2,
                    'take_profit_pct': 4
                })()
                
                self.trading = type('obj', (object,), {
                    'valor_inicial_portfolio': Decimal('10000'),
                    'pares_moedas': ['BTC/USDT', 'ETH/USDT']
                })()
            
            def listar_exchanges_ativos(self):
                return {
                    'binance_simulado': type('obj', (object,), {
                        'nome': 'binance_simulado',
                        'ativo': True
                    })()
                }
        
        return ConfigBasica()
    
    def obter_status_sistema(self) -> Dict[str, Any]:
        """
        Obtém status atual do sistema
        
        Returns:
            Dicionário com status do sistema
        """
        return {
            'status': 'funcionando',
            'ativo': self.ativo,
            'ciclos_executados': self.ciclos_executados,
            'trades_executados': self.trades_executados,
            'exchanges_conectados': len(self.exchanges),
            'ultima_execucao': self.ultima_execucao.isoformat() if self.ultima_execucao else None,
            'valor_portfolio': float(self.gerenciador_risco.valor_atual) if hasattr(self, 'gerenciador_risco') else 0
        }
        
    async def conectar_exchanges(self) -> bool:
        """
        Conecta a todos os exchanges configurados
        
        Returns:
            True se pelo menos um exchange conectou
        """
        with GerenciadorContextoLog(self.logger, "Conectando aos exchanges"):
            exchanges_conectados = 0
            
            for nome, config_exchange in self.configuracao.listar_exchanges_ativos().items():
                try:
                    # Criar adaptador (simulado por enquanto)
                    adaptador = AdaptadorExchangeSimulado(nome, config_exchange)
                    
                    # Tentar conectar
                    if await adaptador.conectar():
                        self.exchanges[nome] = adaptador
                        exchanges_conectados += 1
                        self.logger.info(f"✅ {nome} conectado com sucesso")
                    else:
                        self.logger.error(f"❌ Falha ao conectar com {nome}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Erro ao conectar com {nome}: {str(e)}")
            
            if exchanges_conectados > 0:
                self.logger.info(f"🏦 {exchanges_conectados} exchanges conectados")
                return True
            else:
                self.logger.error("❌ Nenhum exchange conectado!")
                return False
    
    async def inicializar_gerenciamento_risco(self):
        """Inicializa o sistema de gerenciamento de risco"""
        with GerenciadorContextoLog(self.logger, "Inicializando gerenciamento de risco"):
            # Configurar limites iniciais
            self.logger.info(f"🛡️ Tamanho máximo posição: {self.configuracao.risco.tamanho_maximo_posicao_pct}%")
            self.logger.info(f"🛡️ Stop Loss: {self.configuracao.risco.stop_loss_pct}%")
            self.logger.info(f"🛡️ Take Profit: {self.configuracao.risco.take_profit_pct}%")
            self.logger.info(f"🛡️ Perda máxima diária: {self.configuracao.risco.perda_maxima_diaria_pct}%")
    
    @log_performance
    async def executar_ciclo_trading(self):
        """Executa um ciclo completo de trading"""
        try:
            self.ciclos_executados += 1
            self.ultima_execucao = datetime.now()
            
            self.logger.info(f"🔄 Executando ciclo de trading #{self.ciclos_executados}")
            
            # Verificar saúde dos exchanges
            await self._verificar_saude_exchanges()
            
            # Obter dados de mercado
            dados_mercado = await self._obter_dados_mercado()
            
            # Analisar oportunidades
            oportunidades = await self._analisar_oportunidades(dados_mercado)
            
            # Executar trades se houver oportunidades
            if oportunidades:
                await self._executar_trades(oportunidades)
            
            # Atualizar métricas de risco
            await self._atualizar_metricas_portfolio()
            
            # Log de status
            await self._log_status_portfolio()
            
        except Exception as e:
            self.logger.error(f"❌ Erro no ciclo de trading: {str(e)}")
    
    async def _verificar_saude_exchanges(self):
        """Verifica a saúde das conexões com exchanges"""
        for nome, exchange in self.exchanges.items():
            if not exchange.conectado:
                self.logger.warning(f"⚠️ {nome} desconectado - tentando reconectar...")
                await exchange.conectar()
    
    async def _obter_dados_mercado(self) -> Dict[str, Dict]:
        """Obtém dados de mercado de todos os pares configurados"""
        dados_mercado = {}
        
        for par in self.configuracao.trading.pares_moedas:
            for nome_exchange, exchange in self.exchanges.items():
                try:
                    ticker = await exchange.obter_ticker(par)
                    
                    if par not in dados_mercado:
                        dados_mercado[par] = {}
                    
                    dados_mercado[par][nome_exchange] = ticker
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro ao obter ticker {par} de {nome_exchange}: {str(e)}")
        
        return dados_mercado
    
    async def _analisar_oportunidades(self, dados_mercado: Dict) -> List[Dict]:
        """
        Analisa oportunidades de trading baseado nos dados de mercado
        
        Args:
            dados_mercado: Dados de mercado obtidos
            
        Returns:
            Lista de oportunidades de trading
        """
        oportunidades = []
        
        # Estratégia simples: comprar se preço caiu mais de 1% nas últimas verificações
        for par, dados_exchanges in dados_mercado.items():
            for nome_exchange, ticker in dados_exchanges.items():
                try:
                    variacao = ticker.get('variacao_24h', 0)
                    preco = ticker.get('preco', 0)
                    
                    # Oportunidade de compra se caiu mais de 1%
                    if variacao < -1.0 and preco > 0:
                        # Validar com gerenciador de risco
                        quantidade_teste = Decimal('0.001')  # Quantidade pequena para teste
                        
                        valida, motivo, quantidade_ajustada = await self.gerenciador_risco.validar_ordem(
                            par, 'BUY', quantidade_teste, Decimal(str(preco))
                        )
                        
                        if valida:
                            oportunidades.append({
                                'par': par,
                                'exchange': nome_exchange,
                                'acao': 'BUY',
                                'preco': Decimal(str(preco)),
                                'quantidade': quantidade_ajustada,
                                'motivo': f"Queda de {variacao:.2f}%"
                            })
                            
                            self.logger.info(f"💡 Oportunidade: {par} em {nome_exchange} - {motivo}")
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro na análise de {par}: {str(e)}")
        
        return oportunidades
    
    async def _executar_trades(self, oportunidades: List[Dict]):
        """
        Executa trades baseado nas oportunidades identificadas
        
        Args:
            oportunidades: Lista de oportunidades de trading
        """
        for oportunidade in oportunidades[:2]:  # Limitar a 2 trades por ciclo
            try:
                exchange = self.exchanges[oportunidade['exchange']]
                
                # Executar ordem
                resultado = await exchange.colocar_ordem_simulada(
                    simbolo=oportunidade['par'],
                    lado=oportunidade['acao'],
                    quantidade=oportunidade['quantidade'],
                    preco=oportunidade['preco']
                )
                
                # Atualizar estatísticas
                self.trades_executados += 1
                self.valor_total_negociado += oportunidade['quantidade'] * oportunidade['preco']
                
                # Atualizar posição no gerenciador de risco
                await self.gerenciador_risco.atualizar_posicao(
                    oportunidade['par'],
                    oportunidade['quantidade'],
                    oportunidade['preco'],
                    oportunidade['acao']
                )
                
                self.logger.info(f"✅ Trade executado: {resultado['id_ordem']} - {oportunidade['motivo']}")
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao executar trade: {str(e)}")
    
    async def _atualizar_metricas_portfolio(self):
        """Atualiza métricas do portfólio"""
        try:
            # Calcular valor total do portfólio
            valor_total = Decimal('0')
            
            for nome_exchange, exchange in self.exchanges.items():
                saldos = await exchange.obter_saldos()
                
                for moeda, quantidade in saldos.items():
                    if quantidade > 0:
                        if moeda == 'USDT':
                            valor_total += quantidade
                        else:
                            # Tentar obter preço da moeda
                            try:
                                par = f"{moeda}/USDT"
                                if par in self.configuracao.trading.pares_moedas:
                                    ticker = await exchange.obter_ticker(par)
                                    valor_total += quantidade * ticker['preco']
                            except:
                                pass  # Ignorar se não conseguir obter preço
            
            # Atualizar métricas de risco
            await self.gerenciador_risco.atualizar_metricas(valor_total)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar métricas: {str(e)}")
    
    async def _log_status_portfolio(self):
        """Registra status atual do portfólio"""
        try:
            valor_atual = self.gerenciador_risco.valor_atual
            valor_inicial = self.gerenciador_risco.valor_inicial
            drawdown = self.gerenciador_risco.drawdown_atual
            posicoes = len(self.gerenciador_risco.posicoes_abertas)
            
            pnl = valor_atual - valor_inicial
            pnl_pct = (pnl / valor_inicial) * 100 if valor_inicial > 0 else 0
            
            self.logger.info(f"📊 Portfolio: ${valor_atual:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | Drawdown: {drawdown:.2f}% | Posições: {posicoes}")
            self.logger.info(f"📈 Trades: {self.trades_executados} | Volume: ${self.valor_total_negociado:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar status: {str(e)}")
    
    async def finalizar(self):
        """Finaliza o bot de trading de forma segura"""
        try:
            self.logger.info("🔄 Finalizando bot de trading...")
            self.ativo = False
            
            # Desconectar de todos os exchanges
            for nome, exchange in self.exchanges.items():
                await exchange.desconectar()
            
            # Log final
            self.logger.info(f"📊 Resumo final:")
            self.logger.info(f"  • Ciclos executados: {self.ciclos_executados}")
            self.logger.info(f"  • Trades executados: {self.trades_executados}")
            self.logger.info(f"  • Volume negociado: ${self.valor_total_negociado:.2f}")
            
            self.logger.info("✅ Bot finalizado com sucesso")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao finalizar bot: {str(e)}")
