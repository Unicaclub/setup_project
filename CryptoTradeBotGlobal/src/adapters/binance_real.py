"""
Adaptador Real da Binance para o CryptoTradeBotGlobal
Implementa integração completa com a API oficial da Binance (spot), incluindo CRUD de ordens, logs detalhados, tratamento de edge cases e modo simulação/produção.
"""

import os
import time
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceOrderException
except ImportError:
    Client = None
    BinanceAPIException = Exception
    BinanceOrderException = Exception

from src.utils.logger import obter_logger

class BinanceRealAdapter:
    def __init__(self, api_key: str = None, api_secret: str = None, modo_simulacao: bool = False):
        self.logger = obter_logger(__name__)
        self.modo_simulacao = modo_simulacao
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        if not self.modo_simulacao and Client:
            self.client = Client(self.api_key, self.api_secret)
        else:
            self.client = None  # Simulação não conecta
        self.ordens_simuladas: Dict[str, Dict] = {}
        self.logger.info(f"BinanceRealAdapter inicializado. Modo simulação: {self.modo_simulacao}")

    def criar_ordem(self, simbolo: str, lado: str, quantidade: Decimal, preco: Optional[Decimal] = None) -> Dict:
        """
        Cria uma ordem de compra ou venda na Binance (ou simula)
        """
        if self.modo_simulacao:
            ordem_id = f"SIM-{int(time.time()*1000)}"
            ordem = {
                'orderId': ordem_id,
                'symbol': simbolo,
                'side': lado,
                'origQty': str(quantidade),
                'price': str(preco) if preco else None,
                'status': 'FILLED',
                'transactTime': int(time.time()*1000)
            }
            self.ordens_simuladas[ordem_id] = ordem
            self.logger.info(f"[SIMULAÇÃO] Ordem criada: {ordem}")
            return ordem
        try:
            if preco:
                ordem = self.client.create_order(
                    symbol=simbolo,
                    side=lado,
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=float(quantidade),
                    price=str(preco)
                )
            else:
                ordem = self.client.create_order(
                    symbol=simbolo,
                    side=lado,
                    type='MARKET',
                    quantity=float(quantidade)
                )
            self.logger.info(f"Ordem enviada para Binance: {ordem}")
            return ordem
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Erro ao criar ordem na Binance: {e}")
            raise

    def consultar_ordem(self, simbolo: str, ordem_id: str) -> Dict:
        """
        Consulta o status de uma ordem específica
        """
        if self.modo_simulacao:
            ordem = self.ordens_simuladas.get(ordem_id)
            if not ordem:
                self.logger.warning(f"[SIMULAÇÃO] Ordem não encontrada: {ordem_id}")
                return {'status': 'NOT_FOUND'}
            return ordem
        try:
            ordem = self.client.get_order(symbol=simbolo, orderId=ordem_id)
            self.logger.info(f"Consulta de ordem: {ordem}")
            return ordem
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Erro ao consultar ordem: {e}")
            return {'status': 'ERROR', 'erro': str(e)}

    def cancelar_ordem(self, simbolo: str, ordem_id: str) -> Dict:
        """
        Cancela uma ordem aberta
        """
        if self.modo_simulacao:
            ordem = self.ordens_simuladas.pop(ordem_id, None)
            if not ordem:
                self.logger.warning(f"[SIMULAÇÃO] Ordem para cancelar não encontrada: {ordem_id}")
                return {'status': 'NOT_FOUND'}
            ordem['status'] = 'CANCELED'
            self.logger.info(f"[SIMULAÇÃO] Ordem cancelada: {ordem}")
            return ordem
        try:
            resultado = self.client.cancel_order(symbol=simbolo, orderId=ordem_id)
            self.logger.info(f"Ordem cancelada na Binance: {resultado}")
            return resultado
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Erro ao cancelar ordem: {e}")
            return {'status': 'ERROR', 'erro': str(e)}

    def listar_ordens(self, simbolo: str, limite: int = 10) -> List[Dict]:
        """
        Lista ordens recentes para um símbolo
        """
        if self.modo_simulacao:
            ordens = [o for o in self.ordens_simuladas.values() if o['symbol'] == simbolo]
            return ordens[-limite:]
        try:
            ordens = self.client.get_all_orders(symbol=simbolo, limit=limite)
            self.logger.info(f"Ordens recentes: {ordens}")
            return ordens
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Erro ao listar ordens: {e}")
            return []

    def saldo(self) -> Dict:
        """
        Consulta saldo disponível na conta Binance
        """
        if self.modo_simulacao:
            saldo = {'USDT': {'free': '10000.00', 'locked': '0.00'}}
            self.logger.info(f"[SIMULAÇÃO] Saldo: {saldo}")
            return saldo
        try:
            info = self.client.get_account()
            saldos = {b['asset']: b for b in info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
            self.logger.info(f"Saldo real: {saldos}")
            return saldos
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Erro ao consultar saldo: {e}")
            return {}

    def testar_conexao(self) -> bool:
        """
        Testa conexão com a API Binance
        """
        if self.modo_simulacao:
            self.logger.info("[SIMULAÇÃO] Teste de conexão OK.")
            return True
        try:
            self.client.ping()
            self.logger.info("Conexão com Binance OK.")
            return True
        except Exception as e:
            self.logger.error(f"Erro de conexão: {e}")
            return False

# Exemplo de uso:
# adapter = BinanceRealAdapter(modo_simulacao=True)
# adapter.criar_ordem('BTCUSDT', 'BUY', Decimal('0.001'))
"""
Adaptador Binance Real com CCXT
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import ccxt
import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import os
from cryptography.fernet import Fernet

from src.utils.logger import obter_logger, log_performance
from src.core.exceptions import ErroConexao, ErroOrdem, ErroSaldo


class AdaptadorBinanceReal:
    """
    Adaptador para integração real com Binance usando CCXT
    Suporta tanto modo real quanto testnet
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa o adaptador Binance real
        
        Args:
            configuracao: Configurações do adaptador
        """
        self.logger = obter_logger(__name__)
        
        # Configurações básicas
        self.nome = 'Binance Real'
        self.modo_testnet = configuracao.get('testnet', True)
        self.modo_simulacao = configuracao.get('modo_simulacao', False)
        
        # Credenciais (criptografadas)
        self.api_key = self._descriptografar_credencial(configuracao.get('api_key', ''))
        self.api_secret = self._descriptografar_credencial(configuracao.get('api_secret', ''))
        
        # Cliente CCXT
        self.exchange = None
        self.conectado = False
        
        # Cache de dados
        self.cache_precos = {}
        self.cache_saldos = {}
        self.ultima_atualizacao_cache = None
        
        # Estatísticas
        self.total_ordens = 0
        self.ordens_executadas = 0
        self.ordens_canceladas = 0
        self.volume_total = Decimal('0')
        
        # Configurações de trading
        self.taxa_maker = Decimal('0.001')  # 0.1%
        self.taxa_taker = Decimal('0.001')  # 0.1%
        self.min_order_size = Decimal('0.001')  # BTC mínimo
        
        self.logger.info("🏦 Adaptador Binance Real inicializado")
        self.logger.info(f"  • Modo: {'Testnet' if self.modo_testnet else 'Produção'}")
        self.logger.info(f"  • Simulação: {self.modo_simulacao}")
    
    def _descriptografar_credencial(self, credencial_criptografada: str) -> str:
        """
        Descriptografa credenciais de API
        
        Args:
            credencial_criptografada: Credencial criptografada
            
        Returns:
            Credencial descriptografada
        """
        if not credencial_criptografada:
            return ''
        
        try:
            # Usar chave de criptografia do ambiente
            chave_cripto = os.getenv('CRYPTO_KEY')
            if not chave_cripto:
                # Se não houver chave, assumir que a credencial não está criptografada
                return credencial_criptografada
            
            fernet = Fernet(chave_cripto.encode())
            return fernet.decrypt(credencial_criptografada.encode()).decode()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao descriptografar credencial: {str(e)}")
            # Retornar credencial como está (pode não estar criptografada)
            return credencial_criptografada
    
    @log_performance
    async def conectar(self) -> bool:
        """
        Conecta ao Binance usando CCXT
        
        Returns:
            True se conectado com sucesso
        """
        try:
            # Configurar cliente CCXT
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': self.modo_testnet,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # spot, future, delivery
                }
            })
            
            # Testar conexão
            if not self.modo_simulacao:
                # Verificar conectividade
                await self._testar_conexao()
            
            self.conectado = True
            modo_str = "TESTNET" if self.modo_testnet else "PRODUÇÃO"
            self.logger.info(f"🔗 Conectado ao Binance ({modo_str})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao conectar com Binance: {str(e)}")
            self.conectado = False
            return False
    
    async def _testar_conexao(self):
        """Testa a conexão com a API"""
        try:
            # Testar com uma chamada simples
            await self.exchange.fetch_status()
            
            # Verificar permissões da API
            account_info = await self.exchange.fetch_balance()
            self.logger.info("✅ Conexão e permissões verificadas")
            
        except ccxt.AuthenticationError as e:
            raise ErroConexao(f"Erro de autenticação: {str(e)}")
        except ccxt.PermissionDenied as e:
            raise ErroConexao(f"Permissão negada: {str(e)}")
        except Exception as e:
            raise ErroConexao(f"Erro de conexão: {str(e)}")
    
    @log_performance
    async def desconectar(self):
        """Desconecta do Binance"""
        try:
            if self.exchange:
                await self.exchange.close()
            
            self.conectado = False
            self.logger.info("🔌 Desconectado do Binance")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao desconectar: {str(e)}")
    
    @log_performance
    async def obter_preco(self, simbolo: str) -> Decimal:
        """
        Obtém preço atual de um símbolo
        
        Args:
            simbolo: Símbolo do par (ex: BTC/USDT)
            
        Returns:
            Preço atual
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            # Verificar cache
            agora = datetime.now()
            if (simbolo in self.cache_precos and 
                self.ultima_atualizacao_cache and
                (agora - self.ultima_atualizacao_cache).seconds < 5):
                return self.cache_precos[simbolo]
            
            if self.modo_simulacao:
                # Preço simulado
                preco = self._gerar_preco_simulado(simbolo)
            else:
                # Preço real da API
                ticker = await self.exchange.fetch_ticker(simbolo)
                preco = Decimal(str(ticker['last']))
            
            # Atualizar cache
            self.cache_precos[simbolo] = preco
            self.ultima_atualizacao_cache = agora
            
            return preco
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter preço de {simbolo}: {str(e)}")
            raise ErroConexao(f"Erro ao obter preço: {str(e)}")
    
    def _gerar_preco_simulado(self, simbolo: str) -> Decimal:
        """Gera preço simulado para testes"""
        import random
        
        precos_base = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
            'BNB/USDT': 300,
            'ADA/USDT': 0.5,
            'DOT/USDT': 7.0
        }
        
        preco_base = precos_base.get(simbolo, 100)
        variacao = random.uniform(-0.02, 0.02)  # ±2%
        preco_simulado = preco_base * (1 + variacao)
        
        return Decimal(str(round(preco_simulado, 2)))
    
    @log_performance
    async def obter_saldo(self) -> Dict[str, Decimal]:
        """
        Obtém saldos da conta
        
        Returns:
            Dicionário com saldos por moeda
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            if self.modo_simulacao:
                # Saldos simulados
                return {
                    'USDT': Decimal('10000'),
                    'BTC': Decimal('0'),
                    'ETH': Decimal('0'),
                    'BNB': Decimal('0')
                }
            
            # Saldos reais da API
            balance = await self.exchange.fetch_balance()
            
            saldos = {}
            for moeda, info in balance.items():
                if moeda != 'info' and info['total'] > 0:
                    saldos[moeda] = Decimal(str(info['total']))
            
            # Cache dos saldos
            self.cache_saldos = saldos
            
            return saldos
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter saldos: {str(e)}")
            raise ErroConexao(f"Erro ao obter saldos: {str(e)}")
    
    @log_performance
    async def executar_ordem(self, simbolo: str, lado: str, quantidade: float, 
                           preco: Optional[float] = None, tipo: str = 'market') -> Dict[str, Any]:
        """
        Executa uma ordem real no Binance
        
        Args:
            simbolo: Par de trading (ex: BTC/USDT)
            lado: 'buy' ou 'sell'
            quantidade: Quantidade a negociar
            preco: Preço (para ordens limit)
            tipo: Tipo da ordem ('market', 'limit')
            
        Returns:
            Informações da ordem executada
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            # Validações básicas
            if quantidade < float(self.min_order_size):
                raise ErroOrdem(f"Quantidade mínima: {self.min_order_size}")
            
            if self.modo_simulacao:
                # Simular execução
                return await self._simular_ordem(simbolo, lado, quantidade, preco)
            
            # Executar ordem real
            if tipo == 'market':
                ordem = await self.exchange.create_market_order(simbolo, lado, quantidade)
            elif tipo == 'limit':
                if not preco:
                    raise ErroOrdem("Preço obrigatório para ordens limit")
                ordem = await self.exchange.create_limit_order(simbolo, lado, quantidade, preco)
            else:
                raise ErroOrdem(f"Tipo de ordem não suportado: {tipo}")
            
            # Atualizar estatísticas
            self.total_ordens += 1
            if ordem['status'] == 'closed':
                self.ordens_executadas += 1
                self.volume_total += Decimal(str(ordem['cost']))
            
            self.logger.info(f"✅ Ordem executada: {lado} {quantidade} {simbolo}")
            
            return {
                'id': ordem['id'],
                'simbolo': simbolo,
                'lado': lado,
                'quantidade': quantidade,
                'preco': ordem.get('price', preco),
                'status': ordem['status'],
                'timestamp': datetime.now(),
                'taxa': ordem.get('fee', {}).get('cost', 0)
            }
            
        except ccxt.InsufficientFunds as e:
            raise ErroSaldo(f"Saldo insuficiente: {str(e)}")
        except ccxt.InvalidOrder as e:
            raise ErroOrdem(f"Ordem inválida: {str(e)}")
        except Exception as e:
            self.logger.error(f"❌ Erro ao executar ordem: {str(e)}")
            raise ErroOrdem(f"Erro na execução: {str(e)}")
    
    async def _simular_ordem(self, simbolo: str, lado: str, quantidade: float, 
                           preco: Optional[float]) -> Dict[str, Any]:
        """Simula execução de ordem para testes"""
        import uuid
        
        if not preco:
            preco = float(await self.obter_preco(simbolo))
        
        # Simular taxa
        custo = quantidade * preco
        taxa = custo * float(self.taxa_taker)
        
        # Atualizar estatísticas simuladas
        self.total_ordens += 1
        self.ordens_executadas += 1
        self.volume_total += Decimal(str(custo))
        
        return {
            'id': str(uuid.uuid4()),
            'simbolo': simbolo,
            'lado': lado,
            'quantidade': quantidade,
            'preco': preco,
            'status': 'closed',
            'timestamp': datetime.now(),
            'taxa': taxa
        }
    
    @log_performance
    async def cancelar_ordem(self, ordem_id: str, simbolo: str) -> bool:
        """
        Cancela uma ordem
        
        Args:
            ordem_id: ID da ordem
            simbolo: Símbolo da ordem
            
        Returns:
            True se cancelada com sucesso
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            if self.modo_simulacao:
                self.logger.info(f"🔄 Ordem simulada cancelada: {ordem_id}")
                return True
            
            # Cancelar ordem real
            resultado = await self.exchange.cancel_order(ordem_id, simbolo)
            
            self.ordens_canceladas += 1
            self.logger.info(f"❌ Ordem cancelada: {ordem_id}")
            
            return resultado['status'] == 'canceled'
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao cancelar ordem {ordem_id}: {str(e)}")
            return False
    
    @log_performance
    async def obter_historico_ordens(self, simbolo: str, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtém histórico de ordens
        
        Args:
            simbolo: Símbolo para filtrar
            limite: Número máximo de ordens
            
        Returns:
            Lista de ordens históricas
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            if self.modo_simulacao:
                return []  # Histórico vazio para simulação
            
            ordens = await self.exchange.fetch_orders(simbolo, limit=limite)
            
            historico = []
            for ordem in ordens:
                historico.append({
                    'id': ordem['id'],
                    'simbolo': ordem['symbol'],
                    'lado': ordem['side'],
                    'quantidade': ordem['amount'],
                    'preco': ordem['price'],
                    'status': ordem['status'],
                    'timestamp': datetime.fromtimestamp(ordem['timestamp'] / 1000),
                    'taxa': ordem.get('fee', {}).get('cost', 0)
                })
            
            return historico
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter histórico: {str(e)}")
            return []
    
    async def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do adaptador
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            saldos = await self.obter_saldo()
            valor_portfolio = sum(saldos.values())
            
            return {
                'nome': self.nome,
                'conectado': self.conectado,
                'modo_testnet': self.modo_testnet,
                'modo_simulacao': self.modo_simulacao,
                'valor_portfolio': float(valor_portfolio),
                'total_ordens': self.total_ordens,
                'ordens_executadas': self.ordens_executadas,
                'ordens_canceladas': self.ordens_canceladas,
                'volume_total': float(self.volume_total),
                'taxa_sucesso': (self.ordens_executadas / max(self.total_ordens, 1)) * 100,
                'saldos': {moeda: float(saldo) for moeda, saldo in saldos.items()},
                'ultima_atualizacao': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
            return {
                'nome': self.nome,
                'conectado': self.conectado,
                'erro': str(e)
            }
    
    async def obter_informacoes_mercado(self, simbolo: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas do mercado
        
        Args:
            simbolo: Símbolo do par
            
        Returns:
            Informações do mercado
        """
        if not self.conectado:
            raise ErroConexao("Adaptador não está conectado")
        
        try:
            if self.modo_simulacao:
                preco = await self.obter_preco(simbolo)
                return {
                    'simbolo': simbolo,
                    'preco': float(preco),
                    'volume_24h': 1000000,
                    'variacao_24h': 2.5,
                    'alta_24h': float(preco * Decimal('1.05')),
                    'baixa_24h': float(preco * Decimal('0.95')),
                    'timestamp': datetime.now()
                }
            
            # Dados reais do mercado
            ticker = await self.exchange.fetch_ticker(simbolo)
            
            return {
                'simbolo': simbolo,
                'preco': ticker['last'],
                'volume_24h': ticker['quoteVolume'],
                'variacao_24h': ticker['percentage'],
                'alta_24h': ticker['high'],
                'baixa_24h': ticker['low'],
                'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter informações de mercado: {str(e)}")
            raise ErroConexao(f"Erro ao obter dados de mercado: {str(e)}")


# Configuração padrão para Binance real
CONFIGURACAO_PADRAO_BINANCE_REAL = {
    'testnet': True,
    'modo_simulacao': True,
    'api_key': '',
    'api_secret': '',
    'taxa_maker': 0.001,
    'taxa_taker': 0.001,
    'min_order_size': 0.001
}


def criar_adaptador_binance_real(configuracao: Optional[Dict[str, Any]] = None) -> AdaptadorBinanceReal:
    """
    Cria instância do adaptador Binance real
    
    Args:
        configuracao: Configuração personalizada
        
    Returns:
        Instância do adaptador
    """
    config = CONFIGURACAO_PADRAO_BINANCE_REAL.copy()
    if configuracao:
        config.update(configuracao)
    
    return AdaptadorBinanceReal(config)


if __name__ == "__main__":
    # Teste do adaptador Binance real
    import asyncio
    
    async def testar_adaptador():
        """Teste básico do adaptador"""
        print("🧪 Testando Adaptador Binance Real...")
        
        # Configuração de teste
        config = {
            'testnet': True,
            'modo_simulacao': True,
            'api_key': 'test_key',
            'api_secret': 'test_secret'
        }
        
        adaptador = criar_adaptador_binance_real(config)
        
        # Testar conexão
        if await adaptador.conectar():
            print("✅ Conexão estabelecida")
            
            # Testar obtenção de preço
            preco = await adaptador.obter_preco('BTC/USDT')
            print(f"💰 Preço BTC/USDT: ${preco}")
            
            # Testar saldos
            saldos = await adaptador.obter_saldo()
            print(f"💼 Saldos: {saldos}")
            
            # Testar estatísticas
            stats = await adaptador.obter_estatisticas()
            print(f"📊 Estatísticas: {stats['total_ordens']} ordens")
            
            await adaptador.desconectar()
            print("✅ Teste concluído!")
        else:
            print("❌ Falha na conexão")
    
    # Executar teste
    asyncio.run(testar_adaptador())
