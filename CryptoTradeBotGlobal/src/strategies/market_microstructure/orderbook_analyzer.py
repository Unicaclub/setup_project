"""
Analisador de Microestrutura de Mercado - OrderBook
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import deque

from ..base_strategy import BaseStrategy
from ...core.exceptions import StrategyExecutionError


@dataclass
class OrderBookLevel:
    """Representa um nível do orderbook"""
    price: float
    quantity: float
    timestamp: datetime


@dataclass
class OrderBookSnapshot:
    """Snapshot completo do orderbook"""
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    spread: float
    mid_price: float


@dataclass
class ImbalanceSignal:
    """Sinal de desequilíbrio do orderbook"""
    symbol: str
    imbalance_ratio: float
    direction: str  # 'buy' ou 'sell'
    confidence: float
    timestamp: datetime


@dataclass
class LargeOrderDetection:
    """Detecção de ordem grande"""
    symbol: str
    side: str  # 'bid' ou 'ask'
    price: float
    quantity: float
    size_percentile: float
    timestamp: datetime


class OrderBookAnalyzer(BaseStrategy):
    """
    Analisador de microestrutura de mercado baseado em orderbook
    Detecta desequilíbrios, ordens grandes e padrões de liquidez
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o analisador de orderbook
        
        Args:
            config: Configurações da estratégia
        """
        super().__init__()
        self.config = config
        
        # Configurações de análise
        self.depth_levels = config.get('depth_levels', 20)
        self.imbalance_threshold = config.get('imbalance_threshold', 0.3)  # 30%
        self.large_order_percentile = config.get('large_order_percentile', 95)  # 95º percentil
        self.min_spread_bps = config.get('min_spread_bps', 5)  # 5 basis points
        self.history_window = config.get('history_window', 100)  # snapshots
        
        # Símbolos para analisar
        self.symbols = config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
        
        # Histórico de orderbooks
        self.orderbook_history: Dict[str, deque] = {}
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        
        # Métricas calculadas
        self.current_imbalances: Dict[str, ImbalanceSignal] = {}
        self.large_orders: Dict[str, List[LargeOrderDetection]] = {}
        self.liquidity_metrics: Dict[str, Dict[str, float]] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Inicializa estruturas de dados
        for symbol in self.symbols:
            self.orderbook_history[symbol] = deque(maxlen=self.history_window)
            self.price_history[symbol] = deque(maxlen=self.history_window)
            self.volume_history[symbol] = deque(maxlen=self.history_window)
            self.large_orders[symbol] = []
    
    async def analyze(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa o orderbook e detecta padrões
        
        Args:
            orderbook_data: Dados do orderbook por símbolo
            
        Returns:
            Análise completa do orderbook
        """
        try:
            analysis_results = {}
            
            for symbol, orderbook in orderbook_data.items():
                if symbol not in self.symbols:
                    continue
                
                # Processa snapshot do orderbook
                snapshot = self._process_orderbook_snapshot(symbol, orderbook)
                
                # Armazena no histórico
                self.orderbook_history[symbol].append(snapshot)
                self.price_history[symbol].append(snapshot.mid_price)
                
                # Realiza análises
                symbol_analysis = {
                    'imbalance_analysis': self._analyze_imbalance(symbol, snapshot),
                    'large_orders': self._detect_large_orders(symbol, snapshot),
                    'liquidity_metrics': self._calculate_liquidity_metrics(symbol, snapshot),
                    'spread_analysis': self._analyze_spread(symbol, snapshot),
                    'depth_analysis': self._analyze_depth(symbol, snapshot),
                    'flow_toxicity': self._calculate_flow_toxicity(symbol),
                    'timestamp': datetime.now()
                }
                
                analysis_results[symbol] = symbol_analysis
            
            return {
                'analysis': analysis_results,
                'summary': self._generate_summary(analysis_results),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise do orderbook: {str(e)}")
            raise StrategyExecutionError(f"Falha na análise do orderbook: {str(e)}")
    
    def _process_orderbook_snapshot(self, symbol: str, orderbook: Dict[str, Any]) -> OrderBookSnapshot:
        """
        Processa um snapshot do orderbook
        
        Args:
            symbol: Símbolo do ativo
            orderbook: Dados brutos do orderbook
            
        Returns:
            Snapshot processado do orderbook
        """
        timestamp = datetime.now()
        
        # Processa bids (ordens de compra)
        bids = []
        for bid in orderbook.get('bids', [])[:self.depth_levels]:
            bids.append(OrderBookLevel(
                price=float(bid[0]),
                quantity=float(bid[1]),
                timestamp=timestamp
            ))
        
        # Processa asks (ordens de venda)
        asks = []
        for ask in orderbook.get('asks', [])[:self.depth_levels]:
            asks.append(OrderBookLevel(
                price=float(ask[0]),
                quantity=float(ask[1]),
                timestamp=timestamp
            ))
        
        # Calcula spread e preço médio
        if bids and asks:
            best_bid = bids[0].price
            best_ask = asks[0].price
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2
        else:
            spread = 0
            mid_price = 0
        
        return OrderBookSnapshot(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=timestamp,
            spread=spread,
            mid_price=mid_price
        )
    
    def _analyze_imbalance(self, symbol: str, snapshot: OrderBookSnapshot) -> Dict[str, Any]:
        """
        Analisa desequilíbrio do orderbook
        
        Args:
            symbol: Símbolo do ativo
            snapshot: Snapshot do orderbook
            
        Returns:
            Análise de desequilíbrio
        """
        if not snapshot.bids or not snapshot.asks:
            return {'imbalance_ratio': 0, 'direction': 'neutral', 'confidence': 0}
        
        # Calcula volume total de bids e asks
        total_bid_volume = sum(bid.quantity for bid in snapshot.bids)
        total_ask_volume = sum(ask.quantity for ask in snapshot.asks)
        
        if total_bid_volume + total_ask_volume == 0:
            return {'imbalance_ratio': 0, 'direction': 'neutral', 'confidence': 0}
        
        # Calcula ratio de desequilíbrio
        imbalance_ratio = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        
        # Determina direção
        if imbalance_ratio > self.imbalance_threshold:
            direction = 'buy'
            confidence = min(abs(imbalance_ratio), 1.0)
        elif imbalance_ratio < -self.imbalance_threshold:
            direction = 'sell'
            confidence = min(abs(imbalance_ratio), 1.0)
        else:
            direction = 'neutral'
            confidence = 0
        
        # Armazena sinal se significativo
        if confidence > 0:
            signal = ImbalanceSignal(
                symbol=symbol,
                imbalance_ratio=imbalance_ratio,
                direction=direction,
                confidence=confidence,
                timestamp=snapshot.timestamp
            )
            self.current_imbalances[symbol] = signal
        
        return {
            'imbalance_ratio': imbalance_ratio,
            'direction': direction,
            'confidence': confidence,
            'total_bid_volume': total_bid_volume,
            'total_ask_volume': total_ask_volume,
            'signal_strength': abs(imbalance_ratio)
        }
    
    def _detect_large_orders(self, symbol: str, snapshot: OrderBookSnapshot) -> List[Dict[str, Any]]:
        """
        Detecta ordens grandes no orderbook
        
        Args:
            symbol: Símbolo do ativo
            snapshot: Snapshot do orderbook
            
        Returns:
            Lista de ordens grandes detectadas
        """
        large_orders = []
        
        # Coleta todas as quantidades para calcular percentis
        all_quantities = []
        all_quantities.extend([bid.quantity for bid in snapshot.bids])
        all_quantities.extend([ask.quantity for ask in snapshot.asks])
        
        if not all_quantities:
            return large_orders
        
        # Calcula percentil para definir "ordem grande"
        threshold = np.percentile(all_quantities, self.large_order_percentile)
        
        # Verifica bids
        for bid in snapshot.bids:
            if bid.quantity >= threshold:
                detection = LargeOrderDetection(
                    symbol=symbol,
                    side='bid',
                    price=bid.price,
                    quantity=bid.quantity,
                    size_percentile=self.large_order_percentile,
                    timestamp=snapshot.timestamp
                )
                
                large_orders.append({
                    'side': 'bid',
                    'price': bid.price,
                    'quantity': bid.quantity,
                    'size_percentile': self.large_order_percentile,
                    'relative_size': bid.quantity / np.mean(all_quantities)
                })
        
        # Verifica asks
        for ask in snapshot.asks:
            if ask.quantity >= threshold:
                detection = LargeOrderDetection(
                    symbol=symbol,
                    side='ask',
                    price=ask.price,
                    quantity=ask.quantity,
                    size_percentile=self.large_order_percentile,
                    timestamp=snapshot.timestamp
                )
                
                large_orders.append({
                    'side': 'ask',
                    'price': ask.price,
                    'quantity': ask.quantity,
                    'size_percentile': self.large_order_percentile,
                    'relative_size': ask.quantity / np.mean(all_quantities)
                })
        
        # Armazena detecções
        if large_orders:
            if symbol not in self.large_orders:
                self.large_orders[symbol] = []
            self.large_orders[symbol].extend([
                LargeOrderDetection(
                    symbol=symbol,
                    side=order['side'],
                    price=order['price'],
                    quantity=order['quantity'],
                    size_percentile=order['size_percentile'],
                    timestamp=snapshot.timestamp
                ) for order in large_orders
            ])
            
            # Limita histórico
            self.large_orders[symbol] = self.large_orders[symbol][-50:]
        
        return large_orders
    
    def _calculate_liquidity_metrics(self, symbol: str, snapshot: OrderBookSnapshot) -> Dict[str, float]:
        """
        Calcula métricas de liquidez
        
        Args:
            symbol: Símbolo do ativo
            snapshot: Snapshot do orderbook
            
        Returns:
            Métricas de liquidez
        """
        if not snapshot.bids or not snapshot.asks:
            return {}
        
        # Spread absoluto e relativo
        absolute_spread = snapshot.spread
        relative_spread = (absolute_spread / snapshot.mid_price) * 10000  # em basis points
        
        # Profundidade do orderbook
        bid_depth = sum(bid.quantity for bid in snapshot.bids[:5])  # Top 5 níveis
        ask_depth = sum(ask.quantity for ask in snapshot.asks[:5])
        total_depth = bid_depth + ask_depth
        
        # Densidade de liquidez (quantidade por nível de preço)
        if len(snapshot.bids) > 0 and len(snapshot.asks) > 0:
            bid_density = bid_depth / len(snapshot.bids[:5])
            ask_density = ask_depth / len(snapshot.asks[:5])
            avg_density = (bid_density + ask_density) / 2
        else:
            bid_density = ask_density = avg_density = 0
        
        # Resiliência (capacidade de absorver ordens grandes)
        resilience_bid = self._calculate_resilience(snapshot.bids, 'bid')
        resilience_ask = self._calculate_resilience(snapshot.asks, 'ask')
        avg_resilience = (resilience_bid + resilience_ask) / 2
        
        metrics = {
            'absolute_spread': absolute_spread,
            'relative_spread_bps': relative_spread,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': total_depth,
            'bid_density': bid_density,
            'ask_density': ask_density,
            'avg_density': avg_density,
            'resilience_bid': resilience_bid,
            'resilience_ask': resilience_ask,
            'avg_resilience': avg_resilience,
            'liquidity_score': self._calculate_liquidity_score(
                relative_spread, total_depth, avg_resilience
            )
        }
        
        # Armazena métricas
        self.liquidity_metrics[symbol] = metrics
        
        return metrics
    
    def _calculate_resilience(self, levels: List[OrderBookLevel], side: str) -> float:
        """
        Calcula resiliência do orderbook
        
        Args:
            levels: Níveis do orderbook
            side: 'bid' ou 'ask'
            
        Returns:
            Métrica de resiliência
        """
        if not levels:
            return 0
        
        # Simula impacto de uma ordem de mercado
        test_quantity = sum(level.quantity for level in levels[:3]) * 0.1  # 10% dos top 3 níveis
        
        cumulative_quantity = 0
        price_impact = 0
        
        for level in levels:
            if cumulative_quantity >= test_quantity:
                break
            
            remaining_quantity = min(level.quantity, test_quantity - cumulative_quantity)
            cumulative_quantity += remaining_quantity
            
            if side == 'bid':
                price_impact = levels[0].price - level.price
            else:
                price_impact = level.price - levels[0].price
        
        # Resiliência é inversamente proporcional ao impacto no preço
        if price_impact > 0 and levels[0].price > 0:
            resilience = 1 / ((price_impact / levels[0].price) * 10000)  # Normalizado
        else:
            resilience = 100  # Alta resiliência se não há impacto
        
        return min(resilience, 100)  # Limita a 100
    
    def _calculate_liquidity_score(self, spread_bps: float, depth: float, resilience: float) -> float:
        """
        Calcula score geral de liquidez
        
        Args:
            spread_bps: Spread em basis points
            depth: Profundidade total
            resilience: Resiliência média
            
        Returns:
            Score de liquidez (0-100)
        """
        # Normaliza componentes
        spread_score = max(0, 100 - spread_bps)  # Menor spread = melhor
        depth_score = min(100, depth / 1000 * 100)  # Normaliza profundidade
        resilience_score = min(100, resilience)
        
        # Média ponderada
        liquidity_score = (spread_score * 0.4 + depth_score * 0.3 + resilience_score * 0.3)
        
        return max(0, min(100, liquidity_score))
    
    def _analyze_spread(self, symbol: str, snapshot: OrderBookSnapshot) -> Dict[str, Any]:
        """
        Analisa o spread do orderbook
        
        Args:
            symbol: Símbolo do ativo
            snapshot: Snapshot do orderbook
            
        Returns:
            Análise do spread
        """
        if not snapshot.bids or not snapshot.asks:
            return {}
        
        spread_bps = (snapshot.spread / snapshot.mid_price) * 10000
        
        # Classifica spread
        if spread_bps <= 5:
            spread_category = 'tight'
        elif spread_bps <= 20:
            spread_category = 'normal'
        elif spread_bps <= 50:
            spread_category = 'wide'
        else:
            spread_category = 'very_wide'
        
        # Histórico de spreads
        if len(self.orderbook_history[symbol]) > 10:
            recent_spreads = [
                (snap.spread / snap.mid_price) * 10000 
                for snap in list(self.orderbook_history[symbol])[-10:]
                if snap.mid_price > 0
            ]
            
            if recent_spreads:
                avg_spread = np.mean(recent_spreads)
                spread_volatility = np.std(recent_spreads)
                spread_trend = 'widening' if spread_bps > avg_spread * 1.1 else 'tightening' if spread_bps < avg_spread * 0.9 else 'stable'
            else:
                avg_spread = spread_bps
                spread_volatility = 0
                spread_trend = 'stable'
        else:
            avg_spread = spread_bps
            spread_volatility = 0
            spread_trend = 'stable'
        
        return {
            'current_spread_bps': spread_bps,
            'spread_category': spread_category,
            'avg_spread_bps': avg_spread,
            'spread_volatility': spread_volatility,
            'spread_trend': spread_trend,
            'is_tight': spread_bps <= self.min_spread_bps
        }
    
    def _analyze_depth(self, symbol: str, snapshot: OrderBookSnapshot) -> Dict[str, Any]:
        """
        Analisa a profundidade do orderbook
        
        Args:
            symbol: Símbolo do ativo
            snapshot: Snapshot do orderbook
            
        Returns:
            Análise de profundidade
        """
        if not snapshot.bids or not snapshot.asks:
            return {}
        
        # Profundidade por níveis
        depth_levels = [1, 5, 10, len(snapshot.bids)]
        depth_analysis = {}
        
        for level in depth_levels:
            if level <= len(snapshot.bids) and level <= len(snapshot.asks):
                bid_volume = sum(bid.quantity for bid in snapshot.bids[:level])
                ask_volume = sum(ask.quantity for ask in snapshot.asks[:level])
                
                depth_analysis[f'level_{level}'] = {
                    'bid_volume': bid_volume,
                    'ask_volume': ask_volume,
                    'total_volume': bid_volume + ask_volume,
                    'imbalance': (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
                }
        
        # Concentração de liquidez
        if len(snapshot.bids) >= 5 and len(snapshot.asks) >= 5:
            top5_bid_volume = sum(bid.quantity for bid in snapshot.bids[:5])
            total_bid_volume = sum(bid.quantity for bid in snapshot.bids)
            bid_concentration = top5_bid_volume / total_bid_volume if total_bid_volume > 0 else 0
            
            top5_ask_volume = sum(ask.quantity for ask in snapshot.asks[:5])
            total_ask_volume = sum(ask.quantity for ask in snapshot.asks)
            ask_concentration = top5_ask_volume / total_ask_volume if total_ask_volume > 0 else 0
            
            avg_concentration = (bid_concentration + ask_concentration) / 2
        else:
            avg_concentration = 0
        
        return {
            'depth_levels': depth_analysis,
            'liquidity_concentration': avg_concentration,
            'total_levels': {
                'bids': len(snapshot.bids),
                'asks': len(snapshot.asks)
            }
        }
    
    def _calculate_flow_toxicity(self, symbol: str) -> Dict[str, float]:
        """
        Calcula toxicidade do fluxo de ordens
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Métricas de toxicidade do fluxo
        """
        if len(self.price_history[symbol]) < 10:
            return {'toxicity_score': 0, 'price_volatility': 0}
        
        # Calcula volatilidade dos preços
        recent_prices = list(self.price_history[symbol])[-10:]
        price_returns = np.diff(recent_prices) / recent_prices[:-1]
        price_volatility = np.std(price_returns) if len(price_returns) > 1 else 0
        
        # Score de toxicidade baseado na volatilidade
        toxicity_score = min(100, price_volatility * 10000)  # Normalizado
        
        return {
            'toxicity_score': toxicity_score,
            'price_volatility': price_volatility,
            'volatility_category': 'high' if toxicity_score > 50 else 'medium' if toxicity_score > 20 else 'low'
        }
    
    def _generate_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise
        
        Args:
            analysis_results: Resultados da análise por símbolo
            
        Returns:
            Resumo consolidado
        """
        summary = {
            'total_symbols': len(analysis_results),
            'imbalanced_symbols': 0,
            'large_orders_detected': 0,
            'tight_spreads': 0,
            'high_liquidity': 0,
            'alerts': []
        }
        
        for symbol, analysis in analysis_results.items():
            # Conta símbolos com desequilíbrio
            if analysis.get('imbalance_analysis', {}).get('direction') != 'neutral':
                summary['imbalanced_symbols'] += 1
            
            # Conta ordens grandes
            summary['large_orders_detected'] += len(analysis.get('large_orders', []))
            
            # Conta spreads apertados
            if analysis.get('spread_analysis', {}).get('is_tight', False):
                summary['tight_spreads'] += 1
            
            # Conta alta liquidez
            if analysis.get('liquidity_metrics', {}).get('liquidity_score', 0) > 70:
                summary['high_liquidity'] += 1
            
            # Gera alertas
            imbalance = analysis.get('imbalance_analysis', {})
            if imbalance.get('confidence', 0) > 0.5:
                summary['alerts'].append({
                    'type': 'imbalance',
                    'symbol': symbol,
                    'direction': imbalance.get('direction'),
                    'confidence': imbalance.get('confidence')
                })
            
            if len(analysis.get('large_orders', [])) > 0:
                summary['alerts'].append({
                    'type': 'large_orders',
                    'symbol': symbol,
                    'count': len(analysis.get('large_orders', []))
                })
        
        return summary
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de performance do analisador
        
        Returns:
            Métricas de performance
        """
        return {
            'analyzer_name': 'OrderBookAnalyzer',
            'symbols_monitored': len(self.symbols),
            'total_snapshots': sum(len(history) for history in self.orderbook_history.values()),
            'active_imbalances': len(self.current_imbalances),
            'large_orders_detected': sum(len(orders) for orders in self.large_orders.values()),
            'avg_liquidity_score': np.mean([
                metrics.get('liquidity_score', 0) 
                for metrics in self.liquidity_metrics.values()
            ]) if self.liquidity_metrics else 0,
            'configuration': {
                'depth_levels': self.depth_levels,
                'imbalance_threshold': self.imbalance_threshold,
                'large_order_percentile': self.large_order_percentile
            }
        }
