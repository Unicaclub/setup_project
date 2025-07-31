"""
CryptoTradeBotGlobal - Adaptador Base para Exchanges
Sistema completo de integração com exchanges de criptomoedas
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
import aiohttp
import websockets
import ssl
from decimal import Decimal


class TipoOrdem(Enum):
    """Tipos de ordem suportados"""
    MERCADO = "market"
    LIMITE = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMITE = "stop_limit"


class StatusOrdem(Enum):
    """Status possíveis de uma ordem"""
    PENDENTE = "pending"
    ABERTA = "open"
    PREENCHIDA = "filled"
    PARCIALMENTE_PREENCHIDA = "partially_filled"
    CANCELADA = "cancelled"
    REJEITADA = "rejected"
    EXPIRADA = "expired"


class LadoOrdem(Enum):
    """Lado da ordem (compra/venda)"""
    COMPRA = "buy"
    VENDA = "sell"


@dataclass
class InformacoesTicker:
    """Informações de ticker de um par de moedas"""
    simbolo: str
    preco_atual: Decimal
    preco_abertura: Decimal
    preco_maximo: Decimal
    preco_minimo: Decimal
    volume_24h: Decimal
    variacao_24h: Decimal
    timestamp: float = field(default_factory=time.time)
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'simbolo': self.simbolo,
            'preco_atual': float(self.preco_atual),
            'preco_abertura': float(self.preco_abertura),
            'preco_maximo': float(self.preco_maximo),
            'preco_minimo': float(self.preco_minimo),
            'volume_24h': float(self.volume_24h),
            'variacao_24h': float(self.variacao_24h),
            'timestamp': self.timestamp
        }


@dataclass
class OrdemNegociacao:
    """Estrutura de dados para uma ordem de negociação"""
    id_ordem: str
    simbolo: str
    tipo: TipoOrdem
    lado: LadoOrdem
    quantidade: Decimal
    preco: Optional[Decimal] = None
    preco_stop: Optional[Decimal] = None
    status: StatusOrdem = StatusOrdem.PENDENTE
    quantidade_preenchida: Decimal = Decimal('0')
    preco_medio: Decimal = Decimal('0')
    taxa: Decimal = Decimal('0')
    timestamp_criacao: float = field(default_factory=time.time)
    timestamp_atualizacao: float = field(default_factory=time.time)
    metadados: Dict[str, Any] = field(default_factory=dict)
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'id_ordem': self.id_ordem,
            'simbolo': self.simbolo,
            'tipo': self.tipo.value,
            'lado': self.lado.value,
            'quantidade': float(self.quantidade),
            'preco': float(self.preco) if self.preco else None,
            'preco_stop': float(self.preco_stop) if self.preco_stop else None,
            'status': self.status.value,
            'quantidade_preenchida': float(self.quantidade_preenchida),
            'preco_medio': float(self.preco_medio),
            'taxa': float(self.taxa),
            'timestamp_criacao': self.timestamp_criacao,
            'timestamp_atualizacao': self.timestamp_atualizacao,
            'metadados': self.metadados
        }


@dataclass
class LivroOfertas:
    """Estrutura do livro de ofertas (order book)"""
    simbolo: str
    ofertas_compra: List[Tuple[Decimal, Decimal]]  # [(preco, quantidade), ...]
    ofertas_venda: List[Tuple[Decimal, Decimal]]   # [(preco, quantidade), ...]
    timestamp: float = field(default_factory=time.time)
    
    def melhor_oferta_compra(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Retorna a melhor oferta de compra (maior preço)"""
        return max(self.ofertas_compra, key=lambda x: x[0]) if self.ofertas_compra else None
    
    def melhor_oferta_venda(self) -> Optional[Tuple[Decimal, Decimal]]:
        """Retorna a melhor oferta de venda (menor preço)"""
        return min(self.ofertas_venda, key=lambda x: x[0]) if self.ofertas_venda else None
    
    def spread(self) -> Optional[Decimal]:
        """Calcula o spread entre compra e venda"""
        melhor_compra = self.melhor_oferta_compra()
        melhor_venda = self.melhor_oferta_venda()
        
        if melhor_compra and melhor_venda:
            return melhor_venda[0] - melhor_compra[0]
        return None
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'simbolo': self.simbolo,
            'ofertas_compra': [[float(preco), float(qtd)] for preco, qtd in self.ofertas_compra],
            'ofertas_venda': [[float(preco), float(qtd)] for preco, qtd in self.ofertas_venda],
            'timestamp': self.timestamp,
            'melhor_compra': [float(p), float(q)] if (oferta := self.melhor_oferta_compra()) else None,
            'melhor_venda': [float(p), float(q)] if (oferta := self.melhor_oferta_venda()) else None,
            'spread': float(self.spread()) if self.spread() else None
        }


@dataclass
class SaldoConta:
    """Informações de saldo da conta"""
    moeda: str
    saldo_total: Decimal
    saldo_disponivel: Decimal
    saldo_bloqueado: Decimal
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'moeda': self.moeda,
            'saldo_total': float(self.saldo_total),
            'saldo_disponivel': float(self.saldo_disponivel),
            'saldo_bloqueado': float(self.saldo_bloqueado)
        }


class ExcecaoExchange(Exception):
    """Exceção base para erros de exchange"""
    def __init__(self, mensagem: str, codigo_erro: Optional[str] = None):
        self.mensagem = mensagem
        self.codigo_erro = codigo_erro
        super().__init__(mensagem)


class ExcecaoAutenticacao(ExcecaoExchange):
    """Exceção para erros de autenticação"""
    pass


class ExcecaoRateLimit(ExcecaoExchange):
    """Exceção para erros de rate limiting"""
    pass


class ExcecaoConexao(ExcecaoExchange):
    """Exceção para erros de conexão"""
    pass


class AdaptadorBaseExchange(ABC):
    """
    Classe abstrata base para todos os adaptadores de exchange
    
    Define a interface comum que todos os adaptadores devem implementar
    para garantir consistência e intercambiabilidade entre diferentes exchanges.
    """
    
    def __init__(self, chave_api: str, chave_secreta: str, sandbox: bool = True):
        """
        Inicializa o adaptador base
        
        Args:
            chave_api: Chave da API do exchange
            chave_secreta: Chave secreta da API
            sandbox: Se deve usar o ambiente de teste (sandbox)
        """
        self.chave_api = chave_api
        self.chave_secreta = chave_secreta
        self.sandbox = sandbox
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configurações de conexão
        self.timeout_conexao = 30
        self.max_tentativas = 3
        self.delay_entre_tentativas = 1
        
        # Controle de rate limiting
        self.limite_requisicoes_por_segundo = 10
        self.ultima_requisicao = 0
        self.contador_requisicoes = 0
        
        # Status da conexão
        self.conectado = False
        self.websocket_conectado = False
        
        # Sessão HTTP
        self.sessao_http: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # Cache de dados
        self.cache_tickers: Dict[str, InformacoesTicker] = {}
        self.cache_livros_ofertas: Dict[str, LivroOfertas] = {}
        self.cache_saldos: Dict[str, SaldoConta] = {}
        
        # Configurações específicas do exchange
        self.nome_exchange = "base"
        self.url_base_api = ""
        self.url_websocket = ""
        self.pares_suportados: List[str] = []
        self.tipos_ordem_suportados: List[TipoOrdem] = []
        
    async def __aenter__(self):
        """Context manager - entrada"""
        await self.conectar()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager - saída"""
        await self.desconectar()
    
    # ==================== MÉTODOS ABSTRATOS ====================
    
    @abstractmethod
    async def conectar(self) -> bool:
        """
        Estabelece conexão com o exchange
        
        Returns:
            True se conectado com sucesso
        """
        pass
    
    @abstractmethod
    async def desconectar(self) -> bool:
        """
        Encerra conexão com o exchange
        
        Returns:
            True se desconectado com sucesso
        """
        pass
    
    @abstractmethod
    async def obter_ticker(self, simbolo: str) -> InformacoesTicker:
        """
        Obtém informações de ticker para um símbolo
        
        Args:
            simbolo: Par de moedas (ex: 'BTC/USDT')
            
        Returns:
            Informações do ticker
        """
        pass
    
    @abstractmethod
    async def obter_livro_ofertas(self, simbolo: str, profundidade: int = 20) -> LivroOfertas:
        """
        Obtém o livro de ofertas para um símbolo
        
        Args:
            simbolo: Par de moedas
            profundidade: Número de níveis de preço
            
        Returns:
            Livro de ofertas
        """
        pass
    
    @abstractmethod
    async def colocar_ordem(self, ordem: OrdemNegociacao) -> OrdemNegociacao:
        """
        Coloca uma ordem no exchange
        
        Args:
            ordem: Dados da ordem
            
        Returns:
            Ordem atualizada com ID e status
        """
        pass
    
    @abstractmethod
    async def cancelar_ordem(self, id_ordem: str, simbolo: str) -> bool:
        """
        Cancela uma ordem
        
        Args:
            id_ordem: ID da ordem
            simbolo: Par de moedas
            
        Returns:
            True se cancelada com sucesso
        """
        pass
    
    @abstractmethod
    async def obter_status_ordem(self, id_ordem: str, simbolo: str) -> OrdemNegociacao:
        """
        Obtém o status atual de uma ordem
        
        Args:
            id_ordem: ID da ordem
            simbolo: Par de moedas
            
        Returns:
            Dados atualizados da ordem
        """
        pass
    
    @abstractmethod
    async def obter_saldos(self) -> Dict[str, SaldoConta]:
        """
        Obtém saldos da conta
        
        Returns:
            Dicionário com saldos por moeda
        """
        pass
    
    @abstractmethod
    async def obter_historico_ordens(self, simbolo: Optional[str] = None, 
                                   limite: int = 100) -> List[OrdemNegociacao]:
        """
        Obtém histórico de ordens
        
        Args:
            simbolo: Par de moedas (opcional)
            limite: Número máximo de ordens
            
        Returns:
            Lista de ordens históricas
        """
        pass
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    async def _criar_sessao_http(self) -> aiohttp.ClientSession:
        """Cria sessão HTTP com configurações adequadas"""
        timeout = aiohttp.ClientTimeout(total=self.timeout_conexao)
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        return aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'CryptoTradeBotGlobal/1.0',
                'Content-Type': 'application/json'
            }
        )
    
    async def _fazer_requisicao(self, metodo: str, endpoint: str, 
                              parametros: Optional[Dict] = None,
                              dados: Optional[Dict] = None,
                              headers_extras: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP para a API
        
        Args:
            metodo: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            parametros: Parâmetros da query string
            dados: Dados do corpo da requisição
            headers_extras: Headers adicionais
            
        Returns:
            Resposta da API em formato JSON
        """
        if not self.sessao_http:
            self.sessao_http = await self._criar_sessao_http()
        
        # Controle de rate limiting
        await self._aplicar_rate_limit()
        
        # Preparar URL
        url = f"{self.url_base_api}{endpoint}"
        
        # Preparar headers
        headers = await self._gerar_headers_autenticacao(metodo, endpoint, dados)
        if headers_extras:
            headers.update(headers_extras)
        
        # Fazer requisição com retry
        for tentativa in range(self.max_tentativas):
            try:
                async with self.sessao_http.request(
                    metodo, url, params=parametros, json=dados, headers=headers
                ) as resposta:
                    
                    # Verificar status da resposta
                    if resposta.status == 429:  # Rate limit
                        raise ExcecaoRateLimit("Rate limit excedido")
                    elif resposta.status == 401:  # Não autorizado
                        raise ExcecaoAutenticacao("Credenciais inválidas")
                    elif resposta.status >= 400:
                        texto_erro = await resposta.text()
                        raise ExcecaoExchange(f"Erro HTTP {resposta.status}: {texto_erro}")
                    
                    # Retornar dados JSON
                    return await resposta.json()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if tentativa == self.max_tentativas - 1:
                    raise ExcecaoConexao(f"Falha na conexão após {self.max_tentativas} tentativas: {e}")
                
                await asyncio.sleep(self.delay_entre_tentativas * (tentativa + 1))
        
        raise ExcecaoConexao("Número máximo de tentativas excedido")
    
    async def _aplicar_rate_limit(self):
        """Aplica controle de rate limiting"""
        agora = time.time()
        
        # Reset contador se passou 1 segundo
        if agora - self.ultima_requisicao >= 1:
            self.contador_requisicoes = 0
            self.ultima_requisicao = agora
        
        # Verificar se excedeu o limite
        if self.contador_requisicoes >= self.limite_requisicoes_por_segundo:
            tempo_espera = 1 - (agora - self.ultima_requisicao)
            if tempo_espera > 0:
                await asyncio.sleep(tempo_espera)
                self.contador_requisicoes = 0
                self.ultima_requisicao = time.time()
        
        self.contador_requisicoes += 1
    
    @abstractmethod
    async def _gerar_headers_autenticacao(self, metodo: str, endpoint: str, 
                                        dados: Optional[Dict] = None) -> Dict[str, str]:
        """
        Gera headers de autenticação específicos do exchange
        
        Args:
            metodo: Método HTTP
            endpoint: Endpoint da API
            dados: Dados da requisição
            
        Returns:
            Headers de autenticação
        """
        pass
    
    def _gerar_assinatura_hmac(self, mensagem: str, chave: str, algoritmo: str = 'sha256') -> str:
        """
        Gera assinatura HMAC
        
        Args:
            mensagem: Mensagem a ser assinada
            chave: Chave secreta
            algoritmo: Algoritmo de hash
            
        Returns:
            Assinatura em hexadecimal
        """
        return hmac.new(
            chave.encode('utf-8'),
            mensagem.encode('utf-8'),
            getattr(hashlib, algoritmo)
        ).hexdigest()
    
    def _gerar_timestamp(self) -> int:
        """Gera timestamp atual em milissegundos"""
        return int(time.time() * 1000)
    
    # ==================== MÉTODOS DE WEBSOCKET ====================
    
    async def conectar_websocket(self) -> bool:
        """
        Conecta ao WebSocket do exchange
        
        Returns:
            True se conectado com sucesso
        """
        try:
            if not self.url_websocket:
                self.logger.warning("URL do WebSocket não configurada")
                return False
            
            # Configurar SSL
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Conectar
            self.websocket = await websockets.connect(
                self.url_websocket,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.websocket_conectado = True
            self.logger.info("WebSocket conectado com sucesso")
            
            # Iniciar loop de recebimento de mensagens
            asyncio.create_task(self._loop_websocket())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar WebSocket: {e}")
            return False
    
    async def desconectar_websocket(self) -> bool:
        """
        Desconecta do WebSocket
        
        Returns:
            True se desconectado com sucesso
        """
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            
            self.websocket_conectado = False
            self.websocket = None
            self.logger.info("WebSocket desconectado")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desconectar WebSocket: {e}")
            return False
    
    async def _loop_websocket(self):
        """Loop principal para receber mensagens do WebSocket"""
        try:
            while self.websocket_conectado and self.websocket:
                try:
                    mensagem = await asyncio.wait_for(
                        self.websocket.recv(), timeout=30
                    )
                    
                    # Processar mensagem
                    await self._processar_mensagem_websocket(mensagem)
                    
                except asyncio.TimeoutError:
                    # Enviar ping para manter conexão viva
                    if self.websocket and not self.websocket.closed:
                        await self.websocket.ping()
                    
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning("Conexão WebSocket fechada")
                    break
                    
        except Exception as e:
            self.logger.error(f"Erro no loop WebSocket: {e}")
        finally:
            self.websocket_conectado = False
    
    @abstractmethod
    async def _processar_mensagem_websocket(self, mensagem: str):
        """
        Processa mensagem recebida do WebSocket
        
        Args:
            mensagem: Mensagem JSON recebida
        """
        pass
    
    # ==================== MÉTODOS DE VALIDAÇÃO ====================
    
    def validar_simbolo(self, simbolo: str) -> bool:
        """
        Valida se um símbolo é suportado
        
        Args:
            simbolo: Par de moedas
            
        Returns:
            True se válido
        """
        return simbolo in self.pares_suportados if self.pares_suportados else True
    
    def validar_tipo_ordem(self, tipo: TipoOrdem) -> bool:
        """
        Valida se um tipo de ordem é suportado
        
        Args:
            tipo: Tipo da ordem
            
        Returns:
            True se válido
        """
        return tipo in self.tipos_ordem_suportados if self.tipos_ordem_suportados else True
    
    def validar_quantidade(self, quantidade: Decimal, simbolo: str) -> bool:
        """
        Valida se uma quantidade é válida para o símbolo
        
        Args:
            quantidade: Quantidade da ordem
            simbolo: Par de moedas
            
        Returns:
            True se válida
        """
        return quantidade > 0
    
    def validar_preco(self, preco: Decimal, simbolo: str) -> bool:
        """
        Valida se um preço é válido para o símbolo
        
        Args:
            preco: Preço da ordem
            simbolo: Par de moedas
            
        Returns:
            True se válido
        """
        return preco > 0
    
    # ==================== MÉTODOS DE UTILIDADE ====================
    
    def normalizar_simbolo(self, simbolo: str) -> str:
        """
        Normaliza um símbolo para o formato do exchange
        
        Args:
            simbolo: Símbolo no formato padrão (BTC/USDT)
            
        Returns:
            Símbolo no formato do exchange
        """
        return simbolo.replace('/', '').upper()
    
    def desnormalizar_simbolo(self, simbolo: str) -> str:
        """
        Converte símbolo do exchange para formato padrão
        
        Args:
            simbolo: Símbolo no formato do exchange
            
        Returns:
            Símbolo no formato padrão (BTC/USDT)
        """
        # Implementação básica - deve ser sobrescrita por cada exchange
        if len(simbolo) >= 6:
            return f"{simbolo[:-4]}/{simbolo[-4:]}"
        return simbolo
    
    async def obter_informacoes_exchange(self) -> Dict[str, Any]:
        """
        Obtém informações gerais do exchange
        
        Returns:
            Informações do exchange
        """
        return {
            'nome': self.nome_exchange,
            'conectado': self.conectado,
            'websocket_conectado': self.websocket_conectado,
            'sandbox': self.sandbox,
            'pares_suportados': len(self.pares_suportados),
            'tipos_ordem_suportados': [t.value for t in self.tipos_ordem_suportados],
            'limite_requisicoes': self.limite_requisicoes_por_segundo,
            'url_base': self.url_base_api,
            'url_websocket': self.url_websocket
        }
    
    async def verificar_saude(self) -> Dict[str, Any]:
        """
        Verifica a saúde da conexão com o exchange
        
        Returns:
            Status de saúde
        """
        try:
            # Tentar obter informações básicas
            inicio = time.time()
            await self.obter_saldos()
            latencia = (time.time() - inicio) * 1000
            
            return {
                'status': 'saudavel',
                'conectado': self.conectado,
                'websocket_conectado': self.websocket_conectado,
                'latencia_ms': round(latencia, 2),
                'ultima_verificacao': time.time()
            }
            
        except Exception as e:
            return {
                'status': 'erro',
                'conectado': False,
                'websocket_conectado': False,
                'erro': str(e),
                'ultima_verificacao': time.time()
            }
    
    def __str__(self) -> str:
        """Representação em string do adaptador"""
        return f"{self.__class__.__name__}(exchange={self.nome_exchange}, conectado={self.conectado})"
    
    def __repr__(self) -> str:
        """Representação detalhada do adaptador"""
        return (f"{self.__class__.__name__}("
                f"exchange={self.nome_exchange}, "
                f"conectado={self.conectado}, "
                f"sandbox={self.sandbox}, "
                f"websocket={self.websocket_conectado})")
