"""
Estratégia de Arbitragem Inter-Exchange
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from ..base_strategy import BaseStrategy
from ...core.exceptions import StrategyExecutionError, InsufficientFundsError


@dataclass
class ArbitrageOpportunity:
    """Representa uma oportunidade de arbitragem"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    volume_available: float
    timestamp: datetime


class InterExchangeArb(BaseStrategy):
    """
    Estratégia de arbitragem entre exchanges
    Identifica e executa oportunidades de arbitragem entre diferentes exchanges
    """
    
    def __init__(self, exchanges: Dict[str, Any], config: Dict[str, Any]):
        """
        Inicializa a estratégia de arbitragem
        
        Args:
            exchanges: Dicionário com adaptadores das exchanges
            config: Configurações da estratégia
        """
        super().__init__()
        self.exchanges = exchanges
        self.config = config
        
        # Configurações da estratégia
        self.min_profit_percentage = config.get('min_profit_percentage', 0.5)  # 0.5%
        self.max_position_size = config.get('max_position_size', 1000.0)
        self.min_volume_threshold = config.get('min_volume_threshold', 100.0)
        self.execution_timeout = config.get('execution_timeout', 30)  # segundos
        self.price_update_interval = config.get('price_update_interval', 5)  # segundos
        
        # Símbolos para monitorar
        self.symbols = config.get('symbols', ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'])
        
        # Cache de preços
        self.price_cache: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Oportunidades ativas
        self.active_opportunities: List[ArbitrageOpportunity] = []
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze(self) -> List[ArbitrageOpportunity]:
        """
        Analisa oportunidades de arbitragem entre exchanges
        
        Returns:
            Lista de oportunidades de arbitragem encontradas
        """
        try:
            opportunities = []
            
            # Atualiza preços de todas as exchanges
            await self._update_prices()
            
            # Analisa cada símbolo
            for symbol in self.symbols:
                symbol_opportunities = await self._analyze_symbol(symbol)
                opportunities.extend(symbol_opportunities)
            
            # Filtra e ordena oportunidades
            filtered_opportunities = self._filter_opportunities(opportunities)
            
            self.logger.info(f"Encontradas {len(filtered_opportunities)} oportunidades de arbitragem")
            return filtered_opportunities
            
        except Exception as e:
            self.logger.error(f"Erro na análise de arbitragem: {str(e)}")
            raise StrategyExecutionError(f"Falha na análise de arbitragem: {str(e)}")
    
    async def _update_prices(self):
        """Atualiza preços de todos os símbolos em todas as exchanges"""
        tasks = []
        
        for exchange_name, exchange in self.exchanges.items():
            for symbol in self.symbols:
                task = self._get_exchange_price(exchange_name, exchange, symbol)
                tasks.append(task)
        
        # Executa todas as requisições em paralelo
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _get_exchange_price(self, exchange_name: str, exchange: Any, symbol: str):
        """
        Obtém preço de um símbolo em uma exchange específica
        
        Args:
            exchange_name: Nome da exchange
            exchange: Instância do adaptador da exchange
            symbol: Símbolo para consultar
        """
        try:
            ticker = await exchange.get_ticker(symbol)
            
            if exchange_name not in self.price_cache:
                self.price_cache[exchange_name] = {}
            
            self.price_cache[exchange_name][symbol] = {
                'bid': ticker['bid_price'],
                'ask': ticker['ask_price'],
                'last': ticker['last_price'],
                'volume': ticker['volume_24h'],
                'timestamp': datetime.now()
            }
            
            self.last_update[f"{exchange_name}_{symbol}"] = datetime.now()
            
        except Exception as e:
            self.logger.warning(f"Erro ao obter preço {symbol} da {exchange_name}: {str(e)}")
    
    async def _analyze_symbol(self, symbol: str) -> List[ArbitrageOpportunity]:
        """
        Analisa oportunidades de arbitragem para um símbolo específico
        
        Args:
            symbol: Símbolo para analisar
            
        Returns:
            Lista de oportunidades encontradas para o símbolo
        """
        opportunities = []
        exchange_names = list(self.exchanges.keys())
        
        # Compara preços entre todas as combinações de exchanges
        for i, buy_exchange in enumerate(exchange_names):
            for sell_exchange in exchange_names[i+1:]:
                
                # Verifica se temos dados de preço para ambas as exchanges
                if (buy_exchange not in self.price_cache or 
                    sell_exchange not in self.price_cache or
                    symbol not in self.price_cache[buy_exchange] or
                    symbol not in self.price_cache[sell_exchange]):
                    continue
                
                buy_data = self.price_cache[buy_exchange][symbol]
                sell_data = self.price_cache[sell_exchange][symbol]
                
                # Verifica se os dados são recentes
                if (datetime.now() - buy_data['timestamp']).seconds > 60:
                    continue
                if (datetime.now() - sell_data['timestamp']).seconds > 60:
                    continue
                
                # Calcula oportunidade: comprar na exchange com menor preço, vender na com maior
                buy_price = buy_data['ask']  # Preço para comprar
                sell_price = sell_data['bid']  # Preço para vender
                
                if sell_price > buy_price:
                    profit_percentage = ((sell_price - buy_price) / buy_price) * 100
                    
                    if profit_percentage >= self.min_profit_percentage:
                        # Calcula volume disponível
                        volume_available = min(
                            buy_data['volume'] * 0.01,  # 1% do volume diário
                            sell_data['volume'] * 0.01,
                            self.max_position_size
                        )
                        
                        if volume_available >= self.min_volume_threshold:
                            opportunity = ArbitrageOpportunity(
                                symbol=symbol,
                                buy_exchange=buy_exchange,
                                sell_exchange=sell_exchange,
                                buy_price=buy_price,
                                sell_price=sell_price,
                                profit_percentage=profit_percentage,
                                volume_available=volume_available,
                                timestamp=datetime.now()
                            )
                            opportunities.append(opportunity)
                
                # Verifica também a oportunidade inversa
                buy_price_inv = sell_data['ask']
                sell_price_inv = buy_data['bid']
                
                if sell_price_inv > buy_price_inv:
                    profit_percentage_inv = ((sell_price_inv - buy_price_inv) / buy_price_inv) * 100
                    
                    if profit_percentage_inv >= self.min_profit_percentage:
                        volume_available_inv = min(
                            buy_data['volume'] * 0.01,
                            sell_data['volume'] * 0.01,
                            self.max_position_size
                        )
                        
                        if volume_available_inv >= self.min_volume_threshold:
                            opportunity = ArbitrageOpportunity(
                                symbol=symbol,
                                buy_exchange=sell_exchange,
                                sell_exchange=buy_exchange,
                                buy_price=buy_price_inv,
                                sell_price=sell_price_inv,
                                profit_percentage=profit_percentage_inv,
                                volume_available=volume_available_inv,
                                timestamp=datetime.now()
                            )
                            opportunities.append(opportunity)
        
        return opportunities
    
    def _filter_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """
        Filtra e ordena oportunidades de arbitragem
        
        Args:
            opportunities: Lista de oportunidades brutas
            
        Returns:
            Lista filtrada e ordenada por lucratividade
        """
        # Remove oportunidades duplicadas
        unique_opportunities = []
        seen = set()
        
        for opp in opportunities:
            key = f"{opp.symbol}_{opp.buy_exchange}_{opp.sell_exchange}"
            if key not in seen:
                unique_opportunities.append(opp)
                seen.add(key)
        
        # Ordena por lucratividade (maior primeiro)
        unique_opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
        
        # Limita o número de oportunidades
        max_opportunities = self.config.get('max_opportunities', 5)
        return unique_opportunities[:max_opportunities]
    
    async def execute_trade(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """
        Executa trade de arbitragem
        
        Args:
            opportunity: Oportunidade de arbitragem para executar
            
        Returns:
            Resultado da execução
        """
        try:
            self.logger.info(f"Executando arbitragem: {opportunity.symbol} "
                           f"{opportunity.buy_exchange} -> {opportunity.sell_exchange} "
                           f"Lucro: {opportunity.profit_percentage:.2f}%")
            
            # Calcula quantidade a negociar
            quantity = min(opportunity.volume_available, self.max_position_size)
            
            # Verifica saldos disponíveis
            await self._check_balances(opportunity, quantity)
            
            # Executa ordens simultaneamente
            buy_task = self._place_buy_order(opportunity, quantity)
            sell_task = self._place_sell_order(opportunity, quantity)
            
            # Aguarda execução com timeout
            buy_result, sell_result = await asyncio.wait_for(
                asyncio.gather(buy_task, sell_task),
                timeout=self.execution_timeout
            )
            
            # Calcula resultado
            total_cost = buy_result['quantity'] * buy_result['price']
            total_revenue = sell_result['quantity'] * sell_result['price']
            profit = total_revenue - total_cost
            profit_percentage = (profit / total_cost) * 100
            
            result = {
                'success': True,
                'symbol': opportunity.symbol,
                'buy_exchange': opportunity.buy_exchange,
                'sell_exchange': opportunity.sell_exchange,
                'quantity': min(buy_result['quantity'], sell_result['quantity']),
                'buy_price': buy_result['price'],
                'sell_price': sell_result['price'],
                'total_cost': total_cost,
                'total_revenue': total_revenue,
                'profit': profit,
                'profit_percentage': profit_percentage,
                'execution_time': datetime.now(),
                'buy_order_id': buy_result['order_id'],
                'sell_order_id': sell_result['order_id']
            }
            
            self.logger.info(f"Arbitragem executada com sucesso. Lucro: ${profit:.2f} ({profit_percentage:.2f}%)")
            return result
            
        except asyncio.TimeoutError:
            self.logger.error("Timeout na execução da arbitragem")
            raise StrategyExecutionError("Timeout na execução da arbitragem")
        except Exception as e:
            self.logger.error(f"Erro na execução da arbitragem: {str(e)}")
            raise StrategyExecutionError(f"Falha na execução da arbitragem: {str(e)}")
    
    async def _check_balances(self, opportunity: ArbitrageOpportunity, quantity: float):
        """
        Verifica se há saldo suficiente para executar a arbitragem
        
        Args:
            opportunity: Oportunidade de arbitragem
            quantity: Quantidade a negociar
        """
        # Obtém símbolo base e quote
        base_symbol, quote_symbol = opportunity.symbol.split('/')
        
        # Verifica saldo para compra
        buy_exchange = self.exchanges[opportunity.buy_exchange]
        buy_balance = await buy_exchange.get_balance()
        required_quote = quantity * opportunity.buy_price * 1.01  # 1% margem
        
        if buy_balance.get(quote_symbol, 0) < required_quote:
            raise InsufficientFundsError(
                f"Saldo insuficiente em {opportunity.buy_exchange}: "
                f"Necessário {required_quote:.2f} {quote_symbol}, "
                f"Disponível {buy_balance.get(quote_symbol, 0):.2f}"
            )
        
        # Verifica saldo para venda
        sell_exchange = self.exchanges[opportunity.sell_exchange]
        sell_balance = await sell_exchange.get_balance()
        
        if sell_balance.get(base_symbol, 0) < quantity:
            raise InsufficientFundsError(
                f"Saldo insuficiente em {opportunity.sell_exchange}: "
                f"Necessário {quantity:.6f} {base_symbol}, "
                f"Disponível {sell_balance.get(base_symbol, 0):.6f}"
            )
    
    async def _place_buy_order(self, opportunity: ArbitrageOpportunity, quantity: float) -> Dict[str, Any]:
        """Coloca ordem de compra"""
        buy_exchange = self.exchanges[opportunity.buy_exchange]
        return await buy_exchange.place_order(
            symbol=opportunity.symbol,
            side='buy',
            order_type='market',
            quantity=quantity
        )
    
    async def _place_sell_order(self, opportunity: ArbitrageOpportunity, quantity: float) -> Dict[str, Any]:
        """Coloca ordem de venda"""
        sell_exchange = self.exchanges[opportunity.sell_exchange]
        return await sell_exchange.place_order(
            symbol=opportunity.symbol,
            side='sell',
            order_type='market',
            quantity=quantity
        )
    
    async def monitor_discrepancies(self) -> Dict[str, Any]:
        """
        Monitora discrepâncias de preço entre exchanges
        
        Returns:
            Relatório de discrepâncias encontradas
        """
        try:
            await self._update_prices()
            
            discrepancies = {}
            
            for symbol in self.symbols:
                symbol_discrepancies = []
                exchange_names = list(self.exchanges.keys())
                
                # Coleta preços de todas as exchanges
                prices = {}
                for exchange_name in exchange_names:
                    if (exchange_name in self.price_cache and 
                        symbol in self.price_cache[exchange_name]):
                        prices[exchange_name] = self.price_cache[exchange_name][symbol]['last']
                
                if len(prices) < 2:
                    continue
                
                # Calcula discrepâncias
                min_price = min(prices.values())
                max_price = max(prices.values())
                max_discrepancy = ((max_price - min_price) / min_price) * 100
                
                min_exchange = [k for k, v in prices.items() if v == min_price][0]
                max_exchange = [k for k, v in prices.items() if v == max_price][0]
                
                symbol_discrepancies.append({
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_exchange': min_exchange,
                    'max_exchange': max_exchange,
                    'discrepancy_percentage': max_discrepancy,
                    'timestamp': datetime.now()
                })
                
                discrepancies[symbol] = symbol_discrepancies
            
            return {
                'discrepancies': discrepancies,
                'timestamp': datetime.now(),
                'exchanges_monitored': list(self.exchanges.keys()),
                'symbols_monitored': self.symbols
            }
            
        except Exception as e:
            self.logger.error(f"Erro no monitoramento de discrepâncias: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now()}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de performance da estratégia
        
        Returns:
            Dicionário com métricas de performance
        """
        return {
            'strategy_name': 'InterExchangeArbitrage',
            'active_opportunities': len(self.active_opportunities),
            'exchanges_connected': len(self.exchanges),
            'symbols_monitored': len(self.symbols),
            'min_profit_threshold': self.min_profit_percentage,
            'max_position_size': self.max_position_size,
            'last_analysis': self.last_update,
            'price_cache_size': sum(len(symbols) for symbols in self.price_cache.values())
        }
