"""
Feed de Dados de Mercado
Sistema de alimentação de dados de mercado em tempo real para análise técnica
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from decimal import Decimal
import websockets
import aiohttp
from datetime import datetime, timedelta

from .base_exchange import AdaptadorBaseExchange, InformacoesTicker, LivroOfertas


class TipoFeed(Enum):
    """Tipos de feed de dados"""
    TICKER = "ticker"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    KLINES = "klines"
    VOLUME = "volume"


class StatusFeed(Enum):
    """Status do feed de dados"""
    DESCONECTADO = "desconectado"
    CONECTANDO = "conectando"
    CONECTADO = "conectado"
    ERRO = "erro"
    RECONECTANDO = "reconectando"


@dataclass
class DadosTrade:
    """Dados de uma negociação"""
    simbolo: str
    preco: Decimal
    quantidade: Decimal
    timestamp: float
    lado: str  # 'buy' ou 'sell'
    trade_id: str = ""
    
    def para_dict(self) -> Dict[str, Any]:
        return {
            'simbolo': self.simbolo,
            'preco': float(self.preco),
            'quantidade': float(self.quantidade),
            'timestamp': self.timestamp,
            'lado': self.lado,
            'trade_id': self.trade_id
        }


@dataclass
class DadosKline:
    """Dados de candlestick (kline)"""
    simbolo: str
    abertura: Decimal
    maxima: Decimal
    minima: Decimal
    fechamento: Decimal
    volume: Decimal
    timestamp_abertura: float
    timestamp_fechamento: float
    intervalo: str = "1m"
    numero_trades: int = 0
    
    def para_dict(self) -> Dict[str, Any]:
        return {
            'simbolo': self.simbolo,
            'abertura': float(self.abertura),
            'maxima': float(self.maxima),
            'minima': float(self.minima),
            'fechamento': float(self.fechamento),
            'volume': float(self.volume),
            'timestamp_abertura': self.timestamp_abertura,
            'timestamp_fechamento': self.timestamp_fechamento,
            'intervalo': self.intervalo,
            'numero_trades': self.numero_trades
        }


class FeedDadosMercado:
    """
    Sistema de feed de dados de mercado em tempo real
    
    Características:
    - Múltiplas fontes de dados (exchanges)
    - WebSocket para dados em tempo real
    - Cache inteligente de dados
    - Agregação de dados de múltiplas fontes
    - Sistema de callbacks para notificações
    - Reconexão automática
    """
    
    def __init__(self, adaptadores_exchange: List[AdaptadorBaseExchange]):
        """
        Inicializa o feed de dados de mercado
        
        Args:
            adaptadores_exchange: Lista de adaptadores de exchange
        """
        self.logger = logging.getLogger(__name__)
        self.adaptadores = {adapter.nome_exchange: adapter for adapter in adaptadores_exchange}
        
        # Estado do feed
        self.status = StatusFeed.DESCONECTADO
        self.simbolos_ativos: List[str] = []
        self.tipos_feed_ativos: List[TipoFeed] = []
        
        # Cache de dados
        self.cache_tickers: Dict[str, InformacoesTicker] = {}
        self.cache_orderbooks: Dict[str, LivroOfertas] = {}
        self.cache_trades: Dict[str, List[DadosTrade]] = {}
        self.cache_klines: Dict[str, Dict[str, List[DadosKline]]] = {}  # simbolo -> intervalo -> dados
        
        # Configurações de cache
        self.max_trades_cache = 1000
        self.max_klines_cache = 1000
        self.tempo_expiracao_ticker = 5.0  # segundos
        self.tempo_expiracao_orderbook = 2.0  # segundos
        
        # Callbacks para notificações
        self.callbacks_ticker: List[Callable] = []
        self.callbacks_orderbook: List[Callable] = []
        self.callbacks_trades: List[Callable] = []
        self.callbacks_klines: List[Callable] = []
        
        # Controle de conexões WebSocket
        self.conexoes_ws: Dict[str, Any] = {}
        self.tarefas_ws: List[asyncio.Task] = []
        
        # Métricas
        self.total_mensagens_recebidas = 0
        self.total_erros_conexao = 0
        self.ultima_atualizacao = 0.0
        self.latencia_media = 0.0
        
        # Controle de reconexão
        self.max_tentativas_reconexao = 5
        self.delay_reconexao = 5.0
        
    async def conectar(self, simbolos: List[str], tipos_feed: List[TipoFeed]) -> bool:
        """
        Conecta aos feeds de dados
        
        Args:
            simbolos: Lista de símbolos para monitorar
            tipos_feed: Tipos de feed para ativar
            
        Returns:
            True se conectado com sucesso
        """
        try:
            self.logger.info(f"Conectando feed de dados para {len(simbolos)} símbolos")
            self.status = StatusFeed.CONECTANDO
            
            self.simbolos_ativos = simbolos
            self.tipos_feed_ativos = tipos_feed
            
            # Conectar adaptadores de exchange
            for nome, adaptador in self.adaptadores.items():
                if not adaptador.conectado:
                    await adaptador.conectar()
            
            # Iniciar feeds WebSocket
            await self._iniciar_feeds_websocket()
            
            # Carregar dados históricos iniciais
            await self._carregar_dados_iniciais()
            
            self.status = StatusFeed.CONECTADO
            self.logger.info("Feed de dados conectado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar feed de dados: {e}")
            self.status = StatusFeed.ERRO
            return False
    
    async def desconectar(self):
        """Desconecta todos os feeds"""
        try:
            self.logger.info("Desconectando feed de dados")
            self.status = StatusFeed.DESCONECTADO
            
            # Cancelar tarefas WebSocket
            for tarefa in self.tarefas_ws:
                tarefa.cancel()
            
            if self.tarefas_ws:
                await asyncio.gather(*self.tarefas_ws, return_exceptions=True)
            
            self.tarefas_ws.clear()
            
            # Fechar conexões WebSocket
            for conexao in self.conexoes_ws.values():
                if hasattr(conexao, 'close'):
                    await conexao.close()
            
            self.conexoes_ws.clear()
            
            # Desconectar adaptadores
            for adaptador in self.adaptadores.values():
                await adaptador.desconectar()
            
            self.logger.info("Feed de dados desconectado")
            
        except Exception as e:
            self.logger.error(f"Erro ao desconectar feed: {e}")
    
    async def _iniciar_feeds_websocket(self):
        """Inicia feeds WebSocket para cada exchange"""
        for nome_exchange, adaptador in self.adaptadores.items():
            if hasattr(adaptador, 'conectar_websocket'):
                try:
                    await adaptador.conectar_websocket()
                    
                    # Criar tarefa para processar mensagens
                    tarefa = asyncio.create_task(
                        self._processar_feed_websocket(nome_exchange, adaptador)
                    )
                    self.tarefas_ws.append(tarefa)
                    
                except Exception as e:
                    self.logger.error(f"Erro ao iniciar WebSocket para {nome_exchange}: {e}")
    
    async def _processar_feed_websocket(self, nome_exchange: str, adaptador: AdaptadorBaseExchange):
        """
        Processa mensagens do WebSocket de um exchange
        
        Args:
            nome_exchange: Nome do exchange
            adaptador: Adaptador do exchange
        """
        tentativas_reconexao = 0
        
        while self.status in [StatusFeed.CONECTADO, StatusFeed.RECONECTANDO]:
            try:
                # Simular processamento de mensagens WebSocket
                # Em implementação real, isso seria integrado com o WebSocket do adaptador
                await asyncio.sleep(1)
                
                # Atualizar dados simulados
                await self._simular_atualizacao_dados()
                
                tentativas_reconexao = 0  # Reset contador em caso de sucesso
                
            except Exception as e:
                self.logger.error(f"Erro no feed WebSocket {nome_exchange}: {e}")
                self.total_erros_conexao += 1
                
                # Tentar reconectar
                if tentativas_reconexao < self.max_tentativas_reconexao:
                    tentativas_reconexao += 1
                    self.status = StatusFeed.RECONECTANDO
                    
                    self.logger.info(f"Tentativa de reconexão {tentativas_reconexao}/{self.max_tentativas_reconexao}")
                    await asyncio.sleep(self.delay_reconexao)
                    
                    try:
                        await adaptador.conectar_websocket()
                        self.status = StatusFeed.CONECTADO
                    except Exception as reconect_error:
                        self.logger.error(f"Falha na reconexão: {reconect_error}")
                else:
                    self.logger.error(f"Máximo de tentativas de reconexão excedido para {nome_exchange}")
                    self.status = StatusFeed.ERRO
                    break
    
    async def _simular_atualizacao_dados(self):
        """Simula atualização de dados para demonstração"""
        timestamp_atual = time.time()
        
        for simbolo in self.simbolos_ativos:
            # Simular ticker
            if TipoFeed.TICKER in self.tipos_feed_ativos:
                ticker_simulado = self._gerar_ticker_simulado(simbolo, timestamp_atual)
                await self._processar_ticker(ticker_simulado)
            
            # Simular trades
            if TipoFeed.TRADES in self.tipos_feed_ativos:
                trade_simulado = self._gerar_trade_simulado(simbolo, timestamp_atual)
                await self._processar_trade(trade_simulado)
            
            # Simular klines
            if TipoFeed.KLINES in self.tipos_feed_ativos:
                kline_simulado = self._gerar_kline_simulado(simbolo, timestamp_atual)
                await self._processar_kline(kline_simulado)
    
    def _gerar_ticker_simulado(self, simbolo: str, timestamp: float) -> InformacoesTicker:
        """Gera ticker simulado para demonstração"""
        # Preço base simulado
        preco_base = Decimal('50000') if 'BTC' in simbolo else Decimal('3000')
        
        # Adicionar variação aleatória
        variacao = np.random.normal(0, 0.001)  # 0.1% de volatilidade
        preco_atual = preco_base * (1 + Decimal(str(variacao)))
        
        return InformacoesTicker(
            simbolo=simbolo,
            preco_atual=preco_atual,
            preco_abertura=preco_atual * Decimal('0.999'),
            preco_maximo=preco_atual * Decimal('1.002'),
            preco_minimo=preco_atual * Decimal('0.998'),
            volume_24h=Decimal('1000'),
            variacao_24h=Decimal('0.5'),
            timestamp=timestamp
        )
    
    def _gerar_trade_simulado(self, simbolo: str, timestamp: float) -> DadosTrade:
        """Gera trade simulado para demonstração"""
        preco_base = Decimal('50000') if 'BTC' in simbolo else Decimal('3000')
        variacao = np.random.normal(0, 0.0005)
        preco = preco_base * (1 + Decimal(str(variacao)))
        
        return DadosTrade(
            simbolo=simbolo,
            preco=preco,
            quantidade=Decimal(str(np.random.uniform(0.01, 1.0))),
            timestamp=timestamp,
            lado='buy' if np.random.random() > 0.5 else 'sell',
            trade_id=f"trade_{int(timestamp * 1000)}"
        )
    
    def _gerar_kline_simulado(self, simbolo: str, timestamp: float) -> DadosKline:
        """Gera kline simulado para demonstração"""
        preco_base = Decimal('50000') if 'BTC' in simbolo else Decimal('3000')
        
        # Simular OHLC
        abertura = preco_base
        variacao_max = np.random.uniform(0.001, 0.003)
        variacao_min = np.random.uniform(-0.003, -0.001)
        variacao_close = np.random.uniform(-0.002, 0.002)
        
        maxima = abertura * (1 + Decimal(str(variacao_max)))
        minima = abertura * (1 + Decimal(str(variacao_min)))
        fechamento = abertura * (1 + Decimal(str(variacao_close)))
        
        return DadosKline(
            simbolo=simbolo,
            abertura=abertura,
            maxima=maxima,
            minima=minima,
            fechamento=fechamento,
            volume=Decimal(str(np.random.uniform(100, 1000))),
            timestamp_abertura=timestamp - 60,  # 1 minuto atrás
            timestamp_fechamento=timestamp,
            intervalo="1m",
            numero_trades=np.random.randint(10, 100)
        )
    
    async def _processar_ticker(self, ticker: InformacoesTicker):
        """Processa atualização de ticker"""
        self.cache_tickers[ticker.simbolo] = ticker
        self.total_mensagens_recebidas += 1
        self.ultima_atualizacao = time.time()
        
        # Notificar callbacks
        for callback in self.callbacks_ticker:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(ticker)
                else:
                    callback(ticker)
            except Exception as e:
                self.logger.error(f"Erro no callback de ticker: {e}")
    
    async def _processar_trade(self, trade: DadosTrade):
        """Processa nova negociação"""
        if trade.simbolo not in self.cache_trades:
            self.cache_trades[trade.simbolo] = []
        
        self.cache_trades[trade.simbolo].append(trade)
        
        # Limitar cache
        if len(self.cache_trades[trade.simbolo]) > self.max_trades_cache:
            self.cache_trades[trade.simbolo].pop(0)
        
        self.total_mensagens_recebidas += 1
        
        # Notificar callbacks
        for callback in self.callbacks_trades:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(trade)
                else:
                    callback(trade)
            except Exception as e:
                self.logger.error(f"Erro no callback de trade: {e}")
    
    async def _processar_kline(self, kline: DadosKline):
        """Processa atualização de kline"""
        if kline.simbolo not in self.cache_klines:
            self.cache_klines[kline.simbolo] = {}
        
        if kline.intervalo not in self.cache_klines[kline.simbolo]:
            self.cache_klines[kline.simbolo][kline.intervalo] = []
        
        # Atualizar ou adicionar kline
        klines_intervalo = self.cache_klines[kline.simbolo][kline.intervalo]
        
        # Verificar se é atualização de kline existente
        atualizado = False
        for i, k in enumerate(klines_intervalo):
            if k.timestamp_abertura == kline.timestamp_abertura:
                klines_intervalo[i] = kline
                atualizado = True
                break
        
        if not atualizado:
            klines_intervalo.append(kline)
            
            # Limitar cache
            if len(klines_intervalo) > self.max_klines_cache:
                klines_intervalo.pop(0)
        
        self.total_mensagens_recebidas += 1
        
        # Notificar callbacks
        for callback in self.callbacks_klines:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(kline)
                else:
                    callback(kline)
            except Exception as e:
                self.logger.error(f"Erro no callback de kline: {e}")
    
    async def _carregar_dados_iniciais(self):
        """Carrega dados históricos iniciais"""
        self.logger.info("Carregando dados históricos iniciais")
        
        for simbolo in self.simbolos_ativos:
            try:
                # Carregar dados de múltiplos exchanges se disponível
                for nome_exchange, adaptador in self.adaptadores.items():
                    if TipoFeed.TICKER in self.tipos_feed_ativos:
                        ticker = await adaptador.obter_ticker(simbolo)
                        await self._processar_ticker(ticker)
                    
                    if TipoFeed.ORDERBOOK in self.tipos_feed_ativos:
                        orderbook = await adaptador.obter_livro_ofertas(simbolo)
                        self.cache_orderbooks[simbolo] = orderbook
                    
                    # Quebrar após primeiro exchange bem-sucedido
                    break
                    
            except Exception as e:
                self.logger.error(f"Erro ao carregar dados iniciais para {simbolo}: {e}")
    
    # ==================== MÉTODOS PÚBLICOS ====================
    
    def registrar_callback_ticker(self, callback: Callable):
        """Registra callback para atualizações de ticker"""
        self.callbacks_ticker.append(callback)
    
    def registrar_callback_orderbook(self, callback: Callable):
        """Registra callback para atualizações de orderbook"""
        self.callbacks_orderbook.append(callback)
    
    def registrar_callback_trades(self, callback: Callable):
        """Registra callback para novas negociações"""
        self.callbacks_trades.append(callback)
    
    def registrar_callback_klines(self, callback: Callable):
        """Registra callback para atualizações de klines"""
        self.callbacks_klines.append(callback)
    
    def obter_ticker(self, simbolo: str) -> Optional[InformacoesTicker]:
        """
        Obtém último ticker para um símbolo
        
        Args:
            simbolo: Símbolo da moeda
            
        Returns:
            Informações do ticker ou None
        """
        ticker = self.cache_tickers.get(simbolo)
        
        if ticker:
            # Verificar se não expirou
            if time.time() - ticker.timestamp <= self.tempo_expiracao_ticker:
                return ticker
        
        return None
    
    def obter_orderbook(self, simbolo: str) -> Optional[LivroOfertas]:
        """
        Obtém último orderbook para um símbolo
        
        Args:
            simbolo: Símbolo da moeda
            
        Returns:
            Livro de ofertas ou None
        """
        orderbook = self.cache_orderbooks.get(simbolo)
        
        if orderbook:
            # Verificar se não expirou
            if time.time() - orderbook.timestamp <= self.tempo_expiracao_orderbook:
                return orderbook
        
        return None
    
    def obter_trades_recentes(self, simbolo: str, limite: int = 100) -> List[DadosTrade]:
        """
        Obtém trades recentes para um símbolo
        
        Args:
            simbolo: Símbolo da moeda
            limite: Número máximo de trades
            
        Returns:
            Lista de trades recentes
        """
        trades = self.cache_trades.get(simbolo, [])
        return trades[-limite:] if trades else []
    
    def obter_klines(self, simbolo: str, intervalo: str = "1m", limite: int = 100) -> List[DadosKline]:
        """
        Obtém klines para um símbolo
        
        Args:
            simbolo: Símbolo da moeda
            intervalo: Intervalo dos klines
            limite: Número máximo de klines
            
        Returns:
            Lista de klines
        """
        if simbolo in self.cache_klines and intervalo in self.cache_klines[simbolo]:
            klines = self.cache_klines[simbolo][intervalo]
            return klines[-limite:] if klines else []
        
        return []
    
    def obter_dataframe_klines(self, simbolo: str, intervalo: str = "1m", limite: int = 100) -> pd.DataFrame:
        """
        Obtém klines como DataFrame pandas
        
        Args:
            simbolo: Símbolo da moeda
            intervalo: Intervalo dos klines
            limite: Número máximo de klines
            
        Returns:
            DataFrame com dados OHLCV
        """
        klines = self.obter_klines(simbolo, intervalo, limite)
        
        if not klines:
            return pd.DataFrame()
        
        dados = []
        for kline in klines:
            dados.append({
                'timestamp': kline.timestamp_fechamento,
                'open': float(kline.abertura),
                'high': float(kline.maxima),
                'low': float(kline.minima),
                'close': float(kline.fechamento),
                'volume': float(kline.volume)
            })
        
        df = pd.DataFrame(dados)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do feed
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            'status': self.status.value,
            'simbolos_ativos': len(self.simbolos_ativos),
            'tipos_feed_ativos': [t.value for t in self.tipos_feed_ativos],
            'total_mensagens_recebidas': self.total_mensagens_recebidas,
            'total_erros_conexao': self.total_erros_conexao,
            'ultima_atualizacao': self.ultima_atualizacao,
            'latencia_media': self.latencia_media,
            'cache_stats': {
                'tickers': len(self.cache_tickers),
                'orderbooks': len(self.cache_orderbooks),
                'trades_simbolos': len(self.cache_trades),
                'klines_simbolos': len(self.cache_klines)
            },
            'conexoes_ativas': len(self.conexoes_ws),
            'tarefas_ativas': len([t for t in self.tarefas_ws if not t.done()])
        }
    
    async def verificar_saude(self) -> Dict[str, Any]:
        """
        Verifica saúde do feed
        
        Returns:
            Status de saúde
        """
        tempo_desde_ultima_atualizacao = time.time() - self.ultima_atualizacao
        
        # Determinar status de saúde
        if self.status == StatusFeed.CONECTADO and tempo_desde_ultima_atualizacao < 30:
            status_saude = "saudavel"
        elif self.status == StatusFeed.RECONECTANDO:
            status_saude = "reconectando"
        elif tempo_desde_ultima_atualizacao > 60:
            status_saude = "sem_dados"
        else:
            status_saude = "degradado"
        
        return {
            'status': status_saude,
            'feed_status': self.status.value,
            'tempo_desde_ultima_atualizacao': tempo_desde_ultima_atualizacao,
            'total_erros': self.total_erros_conexao,
            'exchanges_conectados': sum(1 for a in self.adaptadores.values() if a.conectado),
            'total_exchanges': len(self.adaptadores),
            'estatisticas': self.obter_estatisticas()
        }
