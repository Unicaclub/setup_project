# Stub mínimo para testes
class EnsemblePredictor:
    pass
"""
Estratégia de Machine Learning - Ensemble Predictor
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os

from ..base_strategy import BaseStrategy
from ...core.exceptions import StrategyExecutionError


@dataclass
class PredictionSignal:
    """Sinal de predição do ensemble"""
    symbol: str
    predicted_price: float
    current_price: float
    price_change_pct: float
    confidence: float
    direction: str  # 'buy', 'sell', 'hold'
    models_consensus: Dict[str, float]
    timestamp: datetime


@dataclass
class ModelPerformance:
    """Métricas de performance de um modelo"""
    model_name: str
    mse: float
    mae: float
    r2: float
    accuracy: float
    last_updated: datetime


class EnsemblePredictor(BaseStrategy):
    # Métodos abstratos mínimos para compatibilidade com testes
    def _analisar_especifica(self, *args, **kwargs):
        pass

    def _finalizar_especifica(self, *args, **kwargs):
        pass

    def _inicializar_especifica(self, *args, **kwargs):
        pass

    def _validar_configuracao_especifica(self, *args, **kwargs):
        return True
    """
    Estratégia de Machine Learning usando ensemble de modelos
    Combina múltiplos algoritmos para predição de preços
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o preditor ensemble
        
        Args:
            config: Configurações da estratégia
        """
        super().__init__(config)
        self.config = config
        
        # Configurações do modelo
        self.lookback_period = config.get('lookback_period', 50)  # períodos históricos
        self.prediction_horizon = config.get('prediction_horizon', 1)  # períodos à frente
        self.retrain_interval = config.get('retrain_interval', 24)  # horas
        self.min_data_points = config.get('min_data_points', 100)
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        
        # Símbolos para analisar
        self.symbols = config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
        
        # Modelos do ensemble
        self.models = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            'linear_regression': LinearRegression(),
            'ridge_regression': Ridge(alpha=1.0)
        }
        
        # Pesos dos modelos no ensemble
        self.model_weights = config.get('model_weights', {
            'random_forest': 0.3,
            'gradient_boosting': 0.3,
            'linear_regression': 0.2,
            'ridge_regression': 0.2
        })
        
        # Scalers para normalização
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Dados históricos e features
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.features_data: Dict[str, pd.DataFrame] = {}
        
        # Modelos treinados por símbolo
        self.trained_models: Dict[str, Dict[str, Any]] = {}
        self.model_performance: Dict[str, Dict[str, ModelPerformance]] = {}
        
        # Predições recentes
        self.recent_predictions: Dict[str, List[PredictionSignal]] = {}
        
        # Timestamps de último treinamento
        self.last_training: Dict[str, datetime] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Inicializa estruturas
        for symbol in self.symbols:
            self.scalers[symbol] = StandardScaler()
            self.trained_models[symbol] = {}
            self.model_performance[symbol] = {}
            self.recent_predictions[symbol] = []
            self.price_data[symbol] = pd.DataFrame()
            self.features_data[symbol] = pd.DataFrame()
    
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa dados de mercado e gera predições
        
        Args:
            market_data: Dados de mercado por símbolo
            
        Returns:
            Predições e análises do ensemble
        """
        try:
            analysis_results = {}
            
            for symbol in self.symbols:
                if symbol not in market_data:
                    continue
                
                # Atualiza dados históricos
                self._update_price_data(symbol, market_data[symbol])
                
                # Verifica se precisa retreinar
                if self._should_retrain(symbol):
                    await self._train_models(symbol)
                
                # Gera predição se modelos estão treinados
                if symbol in self.trained_models and self.trained_models[symbol]:
                    prediction = await self._generate_prediction(symbol)
                    
                    if prediction:
                        analysis_results[symbol] = {
                            'prediction': prediction,
                            'model_performance': self.model_performance.get(symbol, {}),
                            'data_quality': self._assess_data_quality(symbol),
                            'timestamp': datetime.now()
                        }
            
            return {
                'predictions': analysis_results,
                'ensemble_summary': self._generate_ensemble_summary(),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise do ensemble: {str(e)}")
            raise StrategyExecutionError(f"Falha na análise do ensemble: {str(e)}")
    
    def _update_price_data(self, symbol: str, market_data: Dict[str, Any]):
        """
        Atualiza dados históricos de preços
        
        Args:
            symbol: Símbolo do ativo
            market_data: Dados de mercado atuais
        """
        try:
            # Cria novo registro
            new_data = {
                'timestamp': datetime.now(),
                'open': market_data.get('open', market_data.get('last_price', 0)),
                'high': market_data.get('high', market_data.get('last_price', 0)),
                'low': market_data.get('low', market_data.get('last_price', 0)),
                'close': market_data.get('close', market_data.get('last_price', 0)),
                'volume': market_data.get('volume_24h', 0)
            }
            
            # Adiciona aos dados históricos
            if self.price_data[symbol].empty:
                self.price_data[symbol] = pd.DataFrame([new_data])
            else:
                self.price_data[symbol] = pd.concat([
                    self.price_data[symbol],
                    pd.DataFrame([new_data])
                ], ignore_index=True)
            
            # Limita tamanho do histórico
            max_history = self.lookback_period * 3
            if len(self.price_data[symbol]) > max_history:
                self.price_data[symbol] = self.price_data[symbol].tail(max_history)
            
            # Gera features técnicas
            self._generate_technical_features(symbol)
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar dados de {symbol}: {str(e)}")
    
    def _generate_technical_features(self, symbol: str):
        """
        Gera features técnicas para o modelo
        
        Args:
            symbol: Símbolo do ativo
        """
        try:
            df = self.price_data[symbol].copy()
            
            if len(df) < 20:  # Mínimo para calcular indicadores
                return
            
            # Features de preço
            df['price_change'] = df['close'].pct_change()
            df['price_change_2'] = df['close'].pct_change(2)
            df['price_change_5'] = df['close'].pct_change(5)
            
            # Médias móveis
            df['sma_5'] = df['close'].rolling(5).mean()
            df['sma_10'] = df['close'].rolling(10).mean()
            df['sma_20'] = df['close'].rolling(20).mean()
            
            # Médias móveis exponenciais
            df['ema_5'] = df['close'].ewm(span=5).mean()
            df['ema_10'] = df['close'].ewm(span=10).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], 14)
            
            # MACD
            macd_line, macd_signal = self._calculate_macd(df['close'])
            df['macd'] = macd_line
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_line - macd_signal
            
            # Bollinger Bands
            bb_upper, bb_lower = self._calculate_bollinger_bands(df['close'], 20, 2)
            df['bb_upper'] = bb_upper
            df['bb_lower'] = bb_lower
            df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # Volatilidade
            df['volatility'] = df['close'].rolling(10).std()
            df['volume_change'] = df['volume'].pct_change()
            
            # Features de tempo
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            
            # Remove NaN e armazena
            df = df.dropna()
            self.features_data[symbol] = df
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar features para {symbol}: {str(e)}")
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        return macd_line, macd_signal
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series]:
        """Calcula Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band
    
    def _should_retrain(self, symbol: str) -> bool:
        """
        Verifica se deve retreinar os modelos
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            True se deve retreinar
        """
        # Verifica se nunca treinou
        if symbol not in self.last_training:
            return len(self.features_data.get(symbol, pd.DataFrame())) >= self.min_data_points
        
        # Verifica intervalo de retreinamento
        time_since_training = datetime.now() - self.last_training[symbol]
        return time_since_training.total_seconds() / 3600 >= self.retrain_interval
    
    async def _train_models(self, symbol: str):
        """
        Treina todos os modelos do ensemble
        
        Args:
            symbol: Símbolo do ativo
        """
        try:
            df = self.features_data[symbol]
            
            if len(df) < self.min_data_points:
                self.logger.warning(f"Dados insuficientes para treinar {symbol}: {len(df)} < {self.min_data_points}")
                return
            
            # Prepara features e target
            feature_columns = [
                'price_change', 'price_change_2', 'price_change_5',
                'sma_5', 'sma_10', 'sma_20',
                'ema_5', 'ema_10', 'ema_20',
                'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'bb_position', 'volatility', 'volume_change',
                'hour', 'day_of_week'
            ]
            
            # Filtra colunas existentes
            available_features = [col for col in feature_columns if col in df.columns]
            
            if not available_features:
                self.logger.error(f"Nenhuma feature disponível para {symbol}")
                return
            
            X = df[available_features].values
            y = df['close'].shift(-self.prediction_horizon).dropna().values
            
            # Ajusta X para corresponder ao y
            X = X[:len(y)]
            
            if len(X) < self.min_data_points:
                return
            
            # Divide em treino e teste
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Normaliza features
            self.scalers[symbol].fit(X_train)
            X_train_scaled = self.scalers[symbol].transform(X_train)
            X_test_scaled = self.scalers[symbol].transform(X_test)
            
            # Treina cada modelo
            trained_models = {}
            performance_metrics = {}
            
            for model_name, model in self.models.items():
                try:
                    # Treina modelo
                    model.fit(X_train_scaled, y_train)
                    
                    # Faz predições no conjunto de teste
                    y_pred = model.predict(X_test_scaled)
                    
                    # Calcula métricas
                    mse = mean_squared_error(y_test, y_pred)
                    mae = mean_absolute_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    # Calcula acurácia direcional
                    actual_direction = np.sign(np.diff(y_test))
                    pred_direction = np.sign(np.diff(y_pred))
                    accuracy = np.mean(actual_direction == pred_direction) if len(actual_direction) > 0 else 0
                    
                    # Armazena modelo e métricas
                    trained_models[model_name] = model
                    performance_metrics[model_name] = ModelPerformance(
                        model_name=model_name,
                        mse=mse,
                        mae=mae,
                        r2=r2,
                        accuracy=accuracy,
                        last_updated=datetime.now()
                    )
                    
                    self.logger.info(f"Modelo {model_name} treinado para {symbol} - R²: {r2:.3f}, Acurácia: {accuracy:.3f}")
                    
                except Exception as e:
                    self.logger.error(f"Erro ao treinar modelo {model_name} para {symbol}: {str(e)}")
            
            # Armazena modelos treinados
            if trained_models:
                self.trained_models[symbol] = trained_models
                self.model_performance[symbol] = performance_metrics
                self.last_training[symbol] = datetime.now()
                
                self.logger.info(f"Ensemble treinado para {symbol} com {len(trained_models)} modelos")
            
        except Exception as e:
            self.logger.error(f"Erro no treinamento do ensemble para {symbol}: {str(e)}")
    
    async def _generate_prediction(self, symbol: str) -> Optional[PredictionSignal]:
        """
        Gera predição usando o ensemble
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Sinal de predição ou None
        """
        try:
            if symbol not in self.trained_models or not self.trained_models[symbol]:
                return None
            
            df = self.features_data[symbol]
            if df.empty:
                return None
            
            # Prepara features mais recentes
            feature_columns = [
                'price_change', 'price_change_2', 'price_change_5',
                'sma_5', 'sma_10', 'sma_20',
                'ema_5', 'ema_10', 'ema_20',
                'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'bb_position', 'volatility', 'volume_change',
                'hour', 'day_of_week'
            ]
            
            available_features = [col for col in feature_columns if col in df.columns]
            
            if not available_features:
                return None
            
            latest_features = df[available_features].iloc[-1:].values
            latest_features_scaled = self.scalers[symbol].transform(latest_features)
            
            current_price = df['close'].iloc[-1]
            
            # Gera predições de cada modelo
            model_predictions = {}
            weighted_prediction = 0
            total_weight = 0
            
            for model_name, model in self.trained_models[symbol].items():
                try:
                    prediction = model.predict(latest_features_scaled)[0]
                    model_predictions[model_name] = prediction
                    
                    # Aplica peso baseado na performance
                    weight = self.model_weights.get(model_name, 0.25)
                    performance = self.model_performance[symbol].get(model_name)
                    
                    if performance and performance.r2 > 0:
                        # Ajusta peso baseado no R²
                        weight *= (1 + performance.r2)
                    
                    weighted_prediction += prediction * weight
                    total_weight += weight
                    
                except Exception as e:
                    self.logger.error(f"Erro na predição do modelo {model_name}: {str(e)}")
            
            if total_weight == 0:
                return None
            
            # Predição final do ensemble
            final_prediction = weighted_prediction / total_weight
            
            # Calcula mudança percentual
            price_change_pct = ((final_prediction - current_price) / current_price) * 100
            
            # Determina direção e confiança
            direction = 'buy' if price_change_pct > 1 else 'sell' if price_change_pct < -1 else 'hold'
            
            # Calcula confiança baseada na concordância dos modelos
            predictions_array = np.array(list(model_predictions.values()))
            prediction_std = np.std(predictions_array)
            confidence = max(0, 1 - (prediction_std / current_price))
            
            # Cria sinal de predição
            signal = PredictionSignal(
                symbol=symbol,
                predicted_price=final_prediction,
                current_price=current_price,
                price_change_pct=price_change_pct,
                confidence=confidence,
                direction=direction,
                models_consensus=model_predictions,
                timestamp=datetime.now()
            )
            
            # Armazena predição
            self.recent_predictions[symbol].append(signal)
            if len(self.recent_predictions[symbol]) > 50:
                self.recent_predictions[symbol] = self.recent_predictions[symbol][-50:]
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Erro na geração de predição para {symbol}: {str(e)}")
            return None
    
    def generate_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Gera sinal de compra/venda baseado na predição
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Sinal de trading
        """
        if symbol not in self.recent_predictions or not self.recent_predictions[symbol]:
            return {'action': 'hold', 'confidence': 0, 'reason': 'Sem predições disponíveis'}
        
        latest_prediction = self.recent_predictions[symbol][-1]
        
        # Verifica se a confiança é suficiente
        if latest_prediction.confidence < self.confidence_threshold:
            return {
                'action': 'hold',
                'confidence': latest_prediction.confidence,
                'reason': f'Confiança baixa: {latest_prediction.confidence:.2f} < {self.confidence_threshold}'
            }
        
        # Determina ação baseada na predição
        if latest_prediction.direction == 'buy' and latest_prediction.price_change_pct > 2:
            action = 'buy'
            reason = f'Predição de alta: {latest_prediction.price_change_pct:.2f}%'
        elif latest_prediction.direction == 'sell' and latest_prediction.price_change_pct < -2:
            action = 'sell'
            reason = f'Predição de baixa: {latest_prediction.price_change_pct:.2f}%'
        else:
            action = 'hold'
            reason = f'Mudança pequena: {latest_prediction.price_change_pct:.2f}%'
        
        return {
            'action': action,
            'confidence': latest_prediction.confidence,
            'predicted_price': latest_prediction.predicted_price,
            'current_price': latest_prediction.current_price,
            'price_change_pct': latest_prediction.price_change_pct,
            'reason': reason,
            'timestamp': latest_prediction.timestamp
        }
    
    def evaluate_performance(self, symbol: str) -> Dict[str, Any]:
        """
        Avalia desempenho do ensemble
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Métricas de performance
        """
        if symbol not in self.recent_predictions or not self.recent_predictions[symbol]:
            return {'error': 'Sem predições para avaliar'}
        
        predictions = self.recent_predictions[symbol]
        
        if len(predictions) < 10:
            return {'error': 'Predições insuficientes para avaliação'}
        
        # Calcula métricas de acurácia direcional
        correct_directions = 0
        total_predictions = 0
        
        for i in range(len(predictions) - 1):
            current_pred = predictions[i]
            next_actual = predictions[i + 1].current_price
            
            predicted_direction = 1 if current_pred.predicted_price > current_pred.current_price else -1
            actual_direction = 1 if next_actual > current_pred.current_price else -1
            
            if predicted_direction == actual_direction:
                correct_directions += 1
            total_predictions += 1
        
        directional_accuracy = correct_directions / total_predictions if total_predictions > 0 else 0
        
        # Calcula outras métricas
        avg_confidence = np.mean([p.confidence for p in predictions])
        avg_price_change = np.mean([abs(p.price_change_pct) for p in predictions])
        
        # Performance por modelo
        model_performance = {}
        if symbol in self.model_performance:
            for model_name, perf in self.model_performance[symbol].items():
                model_performance[model_name] = {
                    'r2_score': perf.r2,
                    'accuracy': perf.accuracy,
                    'mse': perf.mse,
                    'mae': perf.mae
                }
        
        return {
            'directional_accuracy': directional_accuracy,
            'avg_confidence': avg_confidence,
            'avg_price_change_pct': avg_price_change,
            'total_predictions': len(predictions),
            'model_performance': model_performance,
            'last_prediction': {
                'timestamp': predictions[-1].timestamp,
                'confidence': predictions[-1].confidence,
                'direction': predictions[-1].direction
            }
        }
    
    def _assess_data_quality(self, symbol: str) -> Dict[str, Any]:
        """
        Avalia qualidade dos dados
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Métricas de qualidade dos dados
        """
        df = self.features_data.get(symbol, pd.DataFrame())
        
        if df.empty:
            return {'quality_score': 0, 'issues': ['Sem dados disponíveis']}
        
        issues = []
        quality_score = 100
        
        # Verifica quantidade de dados
        if len(df) < self.min_data_points:
            issues.append(f'Dados insuficientes: {len(df)} < {self.min_data_points}')
            quality_score -= 30
        
        # Verifica valores nulos
        null_percentage = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if null_percentage > 0.05:  # 5%
            issues.append(f'Muitos valores nulos: {null_percentage:.1%}')
            quality_score -= 20
        
        # Verifica variabilidade dos preços
        price_std = df['close'].std()
        price_mean = df['close'].mean()
        cv = price_std / price_mean if price_mean > 0 else 0
        
        if cv < 0.01:  # Muito pouca variabilidade
            issues.append('Baixa variabilidade nos preços')
            quality_score -= 15
        
        # Verifica recência dos dados
        if not df.empty:
            last_timestamp = pd.to_datetime(df['timestamp'].iloc[-1])
            time_since_last = datetime.now() - last_timestamp
            
            if time_since_last.total_seconds() > 3600:  # 1 hora
                issues.append('Dados desatualizados')
                quality_score -= 25
        
        return {
            'quality_score': max(0, quality_score),
            'data_points': len(df),
            'null_percentage': null_percentage,
            'price_variability': cv,
            'issues': issues
        }
    
    def _generate_ensemble_summary(self) -> Dict[str, Any]:
        """
        Gera resumo do ensemble
        
        Returns:
            Resumo consolidado
        """
        summary = {
            'total_symbols': len(self.symbols),
            'trained_symbols': len(self.trained_models),
            'active_predictions': sum(len(preds) for preds in self.recent_predictions.values()),
            'avg_model_performance': {},
            'last_training_times': {}
        }
        
        # Calcula performance média dos modelos
        all_performances = {}
        for symbol_perfs in self.model_performance.values():
            for model_name, perf in symbol_perfs.items():
                if model_name not in all_performances:
                    all_performances[model_name] = []
                all_performances[model_name].append(perf.r2)
        
        for model_name, r2_scores in all_performances.items():
            summary['avg_model_performance'][model_name] = np.mean(r2_scores)
        
        # Últimos tempos de treinamento
        for symbol, last_time in self.last_training.items():
            summary['last_training_times'][symbol] = last_time
        
        return summary
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de performance da estratégia
        
        Returns:
            Métricas de performance
        """
        return {
            'strategy_name': 'EnsemblePredictor',
            'symbols_monitored': len(self.symbols),
            'models_per_ensemble': len(self.models),
            'total_trained_models': sum(len(models) for models in self.trained_models.values()),
            'total_predictions': sum(len(preds) for preds in self.recent_predictions.values()),
            'configuration': {
                'lookback_period': self.lookback_period,
                'prediction_horizon': self.prediction_horizon,
                'confidence_threshold': self.confidence_threshold,
                'retrain_interval': self.retrain_interval
            },
            'model_weights': self.model_weights
        }
