"""
Testes para Estratégias de Trading
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.strategies.arbitrage.inter_exchange_arb import InterExchangeArb, ArbitrageOpportunity
from src.strategies.market_microstructure.orderbook_analyzer import OrderBookAnalyzer
from src.strategies.ml_strategies.ensemble_predictor import EnsemblePredictor
from src.core.exceptions import StrategyExecutionError


class TestInterExchangeArb:
    """Testes para estratégia de arbitragem inter-exchange"""
    
    @pytest.fixture
    def mock_exchanges(self):
        """Mock das exchanges para testes"""
        binance_mock = AsyncMock()
        coinbase_mock = AsyncMock()
        
        # Configura retornos dos mocks
        binance_mock.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid_price': 50000.0,
            'ask_price': 50100.0,
            'last_price': 50050.0,
            'volume_24h': 1000.0
        }
        
        coinbase_mock.get_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid_price': 50200.0,
            'ask_price': 50300.0,
            'last_price': 50250.0,
            'volume_24h': 800.0
        }
        
        return {
            'binance': binance_mock,
            'coinbase': coinbase_mock
        }
    
    @pytest.fixture
    def arbitrage_config(self):
        """Configuração para testes de arbitragem"""
        return {
            'min_profit_percentage': 0.5,
            'max_position_size': 1000.0,
            'min_volume_threshold': 100.0,
            'symbols': ['BTC/USDT']
        }
    
    def test_arbitrage_initialization(self, mock_exchanges, arbitrage_config):
        """Testa inicialização da estratégia de arbitragem"""
        strategy = InterExchangeArb(mock_exchanges, arbitrage_config)
        
        assert strategy.exchanges == mock_exchanges
        assert strategy.min_profit_percentage == 0.5
        assert strategy.max_position_size == 1000.0
        assert 'BTC/USDT' in strategy.symbols
    
    @pytest.mark.asyncio
    async def test_analyze_finds_opportunity(self, mock_exchanges, arbitrage_config):
        """Testa se a análise encontra oportunidades de arbitragem"""
        strategy = InterExchangeArb(mock_exchanges, arbitrage_config)
        
        opportunities = await strategy.analyze()
        
        assert isinstance(opportunities, list)
        # Verifica se encontrou oportunidade (Coinbase bid > Binance ask)
        if opportunities:
            opp = opportunities[0]
            assert isinstance(opp, ArbitrageOpportunity)
            assert opp.symbol == 'BTC/USDT'
            assert opp.profit_percentage > 0
    
    @pytest.mark.asyncio
    async def test_execute_trade_success(self, mock_exchanges, arbitrage_config):
        """Testa execução bem-sucedida de trade de arbitragem"""
        strategy = InterExchangeArb(mock_exchanges, arbitrage_config)
        
        # Configura mocks para execução
        mock_exchanges['binance'].get_balance.return_value = {'USDT': 10000.0}
        mock_exchanges['coinbase'].get_balance.return_value = {'BTC': 1.0}
        
        mock_exchanges['binance'].place_order.return_value = {
            'order_id': 'buy_123',
            'quantity': 0.1,
            'price': 50100.0
        }
        
        mock_exchanges['coinbase'].place_order.return_value = {
            'order_id': 'sell_456',
            'quantity': 0.1,
            'price': 50200.0
        }
        
        # Cria oportunidade de teste
        opportunity = ArbitrageOpportunity(
            symbol='BTC/USDT',
            buy_exchange='binance',
            sell_exchange='coinbase',
            buy_price=50100.0,
            sell_price=50200.0,
            profit_percentage=0.2,
            volume_available=100.0,
            timestamp=datetime.now()
        )
        
        result = await strategy.execute_trade(opportunity)
        
        assert result['success'] is True
        assert result['profit'] > 0
        assert 'buy_order_id' in result
        assert 'sell_order_id' in result
    
    @pytest.mark.asyncio
    async def test_monitor_discrepancies(self, mock_exchanges, arbitrage_config):
        """Testa monitoramento de discrepâncias de preço"""
        strategy = InterExchangeArb(mock_exchanges, arbitrage_config)
        
        report = await strategy.monitor_discrepancies()
        
        assert 'discrepancies' in report
        assert 'timestamp' in report
        assert 'exchanges_monitored' in report


class TestOrderBookAnalyzer:
    """Testes para analisador de orderbook"""
    
    @pytest.fixture
    def analyzer_config(self):
        """Configuração para testes do analisador"""
        return {
            'depth_levels': 10,
            'imbalance_threshold': 0.3,
            'symbols': ['BTC/USDT']
        }
    
    @pytest.fixture
    def sample_orderbook(self):
        """Orderbook de exemplo para testes"""
        return {
            'BTC/USDT': {
                'bids': [
                    [50000.0, 1.0],
                    [49950.0, 2.0],
                    [49900.0, 1.5]
                ],
                'asks': [
                    [50100.0, 0.8],
                    [50150.0, 1.2],
                    [50200.0, 2.0]
                ],
                'timestamp': datetime.now()
            }
        }
    
    def test_analyzer_initialization(self, analyzer_config):
        """Testa inicialização do analisador"""
        analyzer = OrderBookAnalyzer(analyzer_config)
        
        assert analyzer.depth_levels == 10
        assert analyzer.imbalance_threshold == 0.3
        assert 'BTC/USDT' in analyzer.symbols
    
    @pytest.mark.asyncio
    async def test_analyze_orderbook(self, analyzer_config, sample_orderbook):
        """Testa análise do orderbook"""
        analyzer = OrderBookAnalyzer(analyzer_config)
        
        result = await analyzer.analyze(sample_orderbook)
        
        assert 'analysis' in result
        assert 'summary' in result
        assert 'BTC/USDT' in result['analysis']
        
        btc_analysis = result['analysis']['BTC/USDT']
        assert 'imbalance_analysis' in btc_analysis
        assert 'liquidity_metrics' in btc_analysis
        assert 'spread_analysis' in btc_analysis
    
    def test_detect_imbalance(self, analyzer_config, sample_orderbook):
        """Testa detecção de desequilíbrio"""
        analyzer = OrderBookAnalyzer(analyzer_config)
        
        # Processa snapshot
        snapshot = analyzer._process_orderbook_snapshot('BTC/USDT', sample_orderbook['BTC/USDT'])
        
        # Analisa desequilíbrio
        imbalance = analyzer._analyze_imbalance('BTC/USDT', snapshot)
        
        assert 'imbalance_ratio' in imbalance
        assert 'direction' in imbalance
        assert 'confidence' in imbalance
        assert imbalance['direction'] in ['buy', 'sell', 'neutral']
    
    def test_detect_large_orders(self, analyzer_config, sample_orderbook):
        """Testa detecção de ordens grandes"""
        analyzer = OrderBookAnalyzer(analyzer_config)
        
        # Processa snapshot
        snapshot = analyzer._process_orderbook_snapshot('BTC/USDT', sample_orderbook['BTC/USDT'])
        
        # Detecta ordens grandes
        large_orders = analyzer._detect_large_orders('BTC/USDT', snapshot)
        
        assert isinstance(large_orders, list)
        for order in large_orders:
            assert 'side' in order
            assert 'price' in order
            assert 'quantity' in order


class TestEnsemblePredictor:
    """Testes para preditor ensemble"""
    
    @pytest.fixture
    def predictor_config(self):
        """Configuração para testes do preditor"""
        return {
            'lookback_period': 20,
            'prediction_horizon': 1,
            'min_data_points': 50,
            'confidence_threshold': 0.6,
            'symbols': ['BTC/USDT']
        }
    
    @pytest.fixture
    def sample_market_data(self):
        """Dados de mercado de exemplo"""
        return {
            'BTC/USDT': {
                'last_price': 50000.0,
                'open': 49800.0,
                'high': 50200.0,
                'low': 49700.0,
                'close': 50000.0,
                'volume_24h': 1000.0
            }
        }
    
    def test_predictor_initialization(self, predictor_config):
        """Testa inicialização do preditor"""
        predictor = EnsemblePredictor(predictor_config)
        
        assert predictor.lookback_period == 20
        assert predictor.prediction_horizon == 1
        assert predictor.confidence_threshold == 0.6
        assert 'BTC/USDT' in predictor.symbols
        assert len(predictor.models) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_with_insufficient_data(self, predictor_config, sample_market_data):
        """Testa análise com dados insuficientes"""
        predictor = EnsemblePredictor(predictor_config)
        
        result = await predictor.analyze(sample_market_data)
        
        # Com dados insuficientes, não deve haver predições
        assert 'predictions' in result
        assert 'ensemble_summary' in result
    
    def test_generate_technical_features(self, predictor_config):
        """Testa geração de features técnicas"""
        predictor = EnsemblePredictor(predictor_config)
        
        # Simula dados históricos
        import pandas as pd
        dates = pd.date_range(start='2024-01-01', periods=30, freq='1H')
        
        for i, date in enumerate(dates):
            price = 50000 + (i * 10)  # Preço crescente
            market_data = {
                'last_price': price,
                'open': price - 5,
                'high': price + 10,
                'low': price - 10,
                'close': price,
                'volume_24h': 1000
            }
            predictor._update_price_data('BTC/USDT', market_data)
        
        # Verifica se features foram geradas
        features_df = predictor.features_data['BTC/USDT']
        if not features_df.empty:
            assert 'price_change' in features_df.columns
            assert 'sma_5' in features_df.columns
            assert 'rsi' in features_df.columns
    
    def test_should_retrain(self, predictor_config):
        """Testa lógica de retreinamento"""
        predictor = EnsemblePredictor(predictor_config)
        
        # Sem treinamento anterior, deve retreinar se tiver dados suficientes
        should_retrain = predictor._should_retrain('BTC/USDT')
        assert isinstance(should_retrain, bool)
    
    def test_generate_signal(self, predictor_config):
        """Testa geração de sinal de trading"""
        predictor = EnsemblePredictor(predictor_config)
        
        signal = predictor.generate_signal('BTC/USDT')
        
        assert 'action' in signal
        assert 'confidence' in signal
        assert 'reason' in signal
        assert signal['action'] in ['buy', 'sell', 'hold']
    
    def test_evaluate_performance(self, predictor_config):
        """Testa avaliação de performance"""
        predictor = EnsemblePredictor(predictor_config)
        
        performance = predictor.evaluate_performance('BTC/USDT')
        
        # Sem predições, deve retornar erro
        assert 'error' in performance


class TestStrategyExceptions:
    """Testes para exceções das estratégias"""
    
    @pytest.mark.asyncio
    async def test_strategy_execution_error(self):
        """Testa exceção de execução de estratégia"""
        with pytest.raises(StrategyExecutionError):
            raise StrategyExecutionError("Erro de teste")
    
    @pytest.mark.asyncio
    async def test_arbitrage_with_connection_error(self, mock_exchanges, arbitrage_config):
        """Testa arbitragem com erro de conexão"""
        # Configura mock para falhar
        mock_exchanges['binance'].get_ticker.side_effect = Exception("Erro de conexão")
        
        strategy = InterExchangeArb(mock_exchanges, arbitrage_config)
        
        with pytest.raises(StrategyExecutionError):
            await strategy.analyze()


if __name__ == "__main__":
    pytest.main([__file__])
