"""
Adaptador para Exchange OKX
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
import hmac
import hashlib
import base64
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from .base_exchange import BaseExchange
from ...core.exceptions import ExchangeConnectionError, OrderExecutionError


class OkxAdapter(BaseExchange):
    """
    Adaptador para integração com a exchange OKX
    Implementa funcionalidades básicas de trading e dados de mercado
    """
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, sandbox: bool = True):
        """
        Inicializa o adaptador OKX
        
        Args:
            api_key: Chave da API OKX
            secret_key: Chave secreta da API
            passphrase: Frase secreta da API
            sandbox: Se deve usar ambiente de teste
        """
        super().__init__()
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.sandbox = sandbox
        
        # URLs da API
        if sandbox:
            self.base_url = "https://www.okx.com"  # OKX não tem sandbox público
        else:
            self.base_url = "https://www.okx.com"
            
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """
        Gera assinatura para autenticação na API OKX
        
        Args:
            timestamp: Timestamp da requisição
            method: Método HTTP
            request_path: Caminho da requisição
            body: Corpo da requisição
            
        Returns:
            Assinatura base64
        """
        message = timestamp + method + request_path + body
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """
        Gera cabeçalhos para requisições autenticadas
        
        Args:
            method: Método HTTP
            request_path: Caminho da requisição
            body: Corpo da requisição
            
        Returns:
            Dicionário com cabeçalhos
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    async def connect(self) -> bool:
        """
        Estabelece conexão com a API OKX
        
        Returns:
            True se conectado com sucesso
            
        Raises:
            ExchangeConnectionError: Se falhar ao conectar
        """
        try:
            self.session = aiohttp.ClientSession()
            
            # Testa conexão com endpoint público
            async with self.session.get(f"{self.base_url}/api/v5/public/time") as response:
                if response.status == 200:
                    self.connected = True
                    return True
                else:
                    raise ExchangeConnectionError(f"Falha ao conectar com OKX: {response.status}")
                    
        except Exception as e:
            raise ExchangeConnectionError(f"Erro de conexão OKX: {str(e)}")
    
    async def disconnect(self):
        """Desconecta da API OKX"""
        if self.session:
            await self.session.close()
        self.connected = False
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém ticker de um símbolo
        
        Args:
            symbol: Símbolo do par (ex: BTC-USDT)
            
        Returns:
            Dados do ticker
            
        Raises:
            ExchangeConnectionError: Se não conectado
        """
        if not self.connected or not self.session:
            raise ExchangeConnectionError("Não conectado à OKX")
        
        try:
            url = f"{self.base_url}/api/v5/market/ticker"
            params = {"instId": symbol}
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    ticker_data = data['data'][0]
                    return {
                        'symbol': symbol,
                        'last_price': float(ticker_data['last']),
                        'bid_price': float(ticker_data['bidPx']),
                        'ask_price': float(ticker_data['askPx']),
                        'volume_24h': float(ticker_data['vol24h']),
                        'change_24h': float(ticker_data['chg24h']),
                        'timestamp': int(ticker_data['ts'])
                    }
                else:
                    raise ExchangeConnectionError(f"Erro ao obter ticker: {data.get('msg', 'Erro desconhecido')}")
                    
        except Exception as e:
            raise ExchangeConnectionError(f"Erro ao obter ticker OKX: {str(e)}")
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """
        Obtém orderbook de um símbolo
        
        Args:
            symbol: Símbolo do par
            depth: Profundidade do orderbook
            
        Returns:
            Dados do orderbook
        """
        if not self.connected or not self.session:
            raise ExchangeConnectionError("Não conectado à OKX")
        
        try:
            url = f"{self.base_url}/api/v5/market/books"
            params = {"instId": symbol, "sz": str(depth)}
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    book_data = data['data'][0]
                    return {
                        'symbol': symbol,
                        'bids': [[float(bid[0]), float(bid[1])] for bid in book_data['bids']],
                        'asks': [[float(ask[0]), float(ask[1])] for ask in book_data['asks']],
                        'timestamp': int(book_data['ts'])
                    }
                else:
                    raise ExchangeConnectionError(f"Erro ao obter orderbook: {data.get('msg', 'Erro desconhecido')}")
                    
        except Exception as e:
            raise ExchangeConnectionError(f"Erro ao obter orderbook OKX: {str(e)}")
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Coloca uma ordem na exchange
        
        Args:
            symbol: Símbolo do par
            side: 'buy' ou 'sell'
            order_type: 'market' ou 'limit'
            quantity: Quantidade
            price: Preço (obrigatório para ordens limit)
            
        Returns:
            Dados da ordem criada
            
        Raises:
            OrderExecutionError: Se falhar ao executar ordem
        """
        if not self.connected or not self.session:
            raise ExchangeConnectionError("Não conectado à OKX")
        
        try:
            url = f"{self.base_url}/api/v5/trade/order"
            request_path = "/api/v5/trade/order"
            
            # Prepara dados da ordem
            order_data = {
                "instId": symbol,
                "tdMode": "cash",  # Modo de trading à vista
                "side": side,
                "ordType": order_type,
                "sz": str(quantity)
            }
            
            if order_type == "limit" and price:
                order_data["px"] = str(price)
            
            body = json.dumps(order_data)
            headers = self._get_headers("POST", request_path, body)
            
            async with self.session.post(url, data=body, headers=headers) as response:
                data = await response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    order_result = data['data'][0]
                    return {
                        'order_id': order_result['ordId'],
                        'symbol': symbol,
                        'side': side,
                        'type': order_type,
                        'quantity': quantity,
                        'price': price,
                        'status': 'submitted',
                        'timestamp': int(order_result.get('cTime', 0))
                    }
                else:
                    raise OrderExecutionError(f"Erro ao criar ordem: {data.get('msg', 'Erro desconhecido')}")
                    
        except Exception as e:
            raise OrderExecutionError(f"Erro ao executar ordem OKX: {str(e)}")
    
    async def get_balance(self) -> Dict[str, float]:
        """
        Obtém saldo da conta
        
        Returns:
            Dicionário com saldos por moeda
        """
        if not self.connected or not self.session:
            raise ExchangeConnectionError("Não conectado à OKX")
        
        try:
            url = f"{self.base_url}/api/v5/account/balance"
            request_path = "/api/v5/account/balance"
            headers = self._get_headers("GET", request_path)
            
            async with self.session.get(url, headers=headers) as response:
                data = await response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    balances = {}
                    for account in data['data']:
                        for detail in account.get('details', []):
                            currency = detail['ccy']
                            available = float(detail['availBal'])
                            if available > 0:
                                balances[currency] = available
                    return balances
                else:
                    raise ExchangeConnectionError(f"Erro ao obter saldo: {data.get('msg', 'Erro desconhecido')}")
                    
        except Exception as e:
            raise ExchangeConnectionError(f"Erro ao obter saldo OKX: {str(e)}")
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Obtém status de uma ordem
        
        Args:
            order_id: ID da ordem
            symbol: Símbolo do par
            
        Returns:
            Status da ordem
        """
        if not self.connected or not self.session:
            raise ExchangeConnectionError("Não conectado à OKX")
        
        try:
            url = f"{self.base_url}/api/v5/trade/order"
            request_path = "/api/v5/trade/order"
            params = {"instId": symbol, "ordId": order_id}
            headers = self._get_headers("GET", request_path)
            
            async with self.session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    order_data = data['data'][0]
                    return {
                        'order_id': order_data['ordId'],
                        'symbol': order_data['instId'],
                        'side': order_data['side'],
                        'type': order_data['ordType'],
                        'quantity': float(order_data['sz']),
                        'filled_quantity': float(order_data['fillSz']),
                        'price': float(order_data.get('px', 0)),
                        'average_price': float(order_data.get('avgPx', 0)),
                        'status': order_data['state'],
                        'timestamp': int(order_data['cTime'])
                    }
                else:
                    raise ExchangeConnectionError(f"Erro ao obter status da ordem: {data.get('msg', 'Erro desconhecido')}")
                    
        except Exception as e:
            raise ExchangeConnectionError(f"Erro ao obter status da ordem OKX: {str(e)}")
