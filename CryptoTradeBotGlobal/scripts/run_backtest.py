#!/usr/bin/env python3
"""
Script de Backtesting
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger


class BacktestEngine:
    """
    Motor de backtesting para estratégias de trading
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o motor de backtesting
        
        Args:
            config: Configurações do backtest
        """
        self.config = config
        self.logger = setup_logger('backtest')
        
        # Configurações do backtest
        self.start_date = config.get('start_date')
        self.end_date = config.get('end_date')
        self.initial_capital = config.get('initial_capital', 10000.0)
        self.symbols = config.get('symbols', ['BTC/USDT'])
        self.strategies = config.get('strategies', ['trend_following'])
        
        # Resultados
        self.results = {}
        self.trades = []
        self.portfolio_history = []
    
    async def load_historical_data(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Carrega dados históricos para backtesting
        
        Args:
            symbol: Símbolo do ativo
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Lista de dados históricos
        """
        self.logger.info(f"Carregando dados históricos para {symbol} ({start_date} - {end_date})")
        
        # Simula carregamento de dados históricos
        # Em uma implementação real, você carregaria de uma API ou arquivo
        
        import random
        import pandas as pd
        
        # Gera dados simulados para demonstração
        dates = pd.date_range(start=start_date, end=end_date, freq='1H')
        base_price = 50000 if 'BTC' in symbol else 3000
        
        historical_data = []
        current_price = base_price
        
        for date in dates:
            # Simula movimento de preços
            change = random.uniform(-0.02, 0.02)  # ±2%
            current_price *= (1 + change)
            
            volume = random.uniform(100, 1000)
            
            candle = {
                'timestamp': date,
                'open': current_price * random.uniform(0.999, 1.001),
                'high': current_price * random.uniform(1.001, 1.01),
                'low': current_price * random.uniform(0.99, 0.999),
                'close': current_price,
                'volume': volume
            }
            
            historical_data.append(candle)
        
        self.logger.info(f"Carregados {len(historical_data)} pontos de dados para {symbol}")
        return historical_data
    
    async def run_strategy_backtest(self, strategy_name: str, symbol: str, data: List[Dict]) -> Dict[str, Any]:
        """
        Executa backtest de uma estratégia específica
        
        Args:
            strategy_name: Nome da estratégia
            symbol: Símbolo do ativo
            data: Dados históricos
            
        Returns:
            Resultados do backtest
        """
        self.logger.info(f"Executando backtest da estratégia {strategy_name} para {symbol}")
        
        # Simula execução da estratégia
        trades = []
        portfolio_value = self.initial_capital
        position = 0  # 0 = sem posição, 1 = comprado, -1 = vendido
        entry_price = 0
        
        for i, candle in enumerate(data):
            price = candle['close']
            
            # Simula sinais da estratégia
            if strategy_name == 'trend_following':
                signal = self._trend_following_signal(data, i)
            elif strategy_name == 'mean_reversion':
                signal = self._mean_reversion_signal(data, i)
            else:
                signal = 'hold'
            
            # Executa trades baseado no sinal
            if signal == 'buy' and position <= 0:
                if position == -1:  # Fecha posição vendida
                    profit = (entry_price - price) * abs(position)
                    portfolio_value += profit
                    trades.append({
                        'timestamp': candle['timestamp'],
                        'action': 'close_short',
                        'price': price,
                        'quantity': abs(position),
                        'profit': profit
                    })
                
                # Abre posição comprada
                quantity = portfolio_value * 0.95 / price  # 95% do capital
                position = quantity
                entry_price = price
                trades.append({
                    'timestamp': candle['timestamp'],
                    'action': 'buy',
                    'price': price,
                    'quantity': quantity,
                    'profit': 0
                })
            
            elif signal == 'sell' and position >= 0:
                if position > 0:  # Fecha posição comprada
                    profit = (price - entry_price) * position
                    portfolio_value += profit
                    trades.append({
                        'timestamp': candle['timestamp'],
                        'action': 'close_long',
                        'price': price,
                        'quantity': position,
                        'profit': profit
                    })
                
                # Abre posição vendida (se permitido)
                quantity = portfolio_value * 0.95 / price
                position = -quantity
                entry_price = price
                trades.append({
                    'timestamp': candle['timestamp'],
                    'action': 'sell',
                    'price': price,
                    'quantity': quantity,
                    'profit': 0
                })
            
            # Calcula valor atual do portfólio
            if position > 0:
                current_value = portfolio_value + (price - entry_price) * position
            elif position < 0:
                current_value = portfolio_value + (entry_price - price) * abs(position)
            else:
                current_value = portfolio_value
            
            # Armazena histórico do portfólio
            if i % 24 == 0:  # A cada 24 horas
                self.portfolio_history.append({
                    'timestamp': candle['timestamp'],
                    'value': current_value,
                    'position': position,
                    'price': price
                })
        
        # Fecha posição final se necessário
        if position != 0:
            final_price = data[-1]['close']
            if position > 0:
                profit = (final_price - entry_price) * position
            else:
                profit = (entry_price - final_price) * abs(position)
            
            portfolio_value += profit
            trades.append({
                'timestamp': data[-1]['timestamp'],
                'action': 'close_final',
                'price': final_price,
                'quantity': abs(position),
                'profit': profit
            })
        
        # Calcula métricas de performance
        total_return = (portfolio_value - self.initial_capital) / self.initial_capital * 100
        total_trades = len([t for t in trades if t['action'] in ['buy', 'sell']])
        winning_trades = len([t for t in trades if t['profit'] > 0])
        win_rate = (winning_trades / len(trades)) * 100 if trades else 0
        
        # Calcula drawdown máximo
        peak_value = self.initial_capital
        max_drawdown = 0
        
        for record in self.portfolio_history:
            if record['value'] > peak_value:
                peak_value = record['value']
            
            drawdown = (peak_value - record['value']) / peak_value * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        results = {
            'strategy': strategy_name,
            'symbol': symbol,
            'initial_capital': self.initial_capital,
            'final_value': portfolio_value,
            'total_return_pct': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'trades': trades,
            'portfolio_history': self.portfolio_history[-100:]  # Últimos 100 registros
        }
        
        self.logger.info(f"Backtest concluído - Retorno: {total_return:.2f}%, Trades: {total_trades}, Win Rate: {win_rate:.1f}%")
        return results
    
    def _trend_following_signal(self, data: List[Dict], index: int) -> str:
        """
        Simula sinal de estratégia trend following
        
        Args:
            data: Dados históricos
            index: Índice atual
            
        Returns:
            Sinal ('buy', 'sell', 'hold')
        """
        if index < 20:  # Precisa de histórico mínimo
            return 'hold'
        
        # Calcula médias móveis simples
        short_ma = sum(candle['close'] for candle in data[index-10:index]) / 10
        long_ma = sum(candle['close'] for candle in data[index-20:index]) / 20
        
        current_price = data[index]['close']
        
        if short_ma > long_ma and current_price > short_ma:
            return 'buy'
        elif short_ma < long_ma and current_price < short_ma:
            return 'sell'
        else:
            return 'hold'
    
    def _mean_reversion_signal(self, data: List[Dict], index: int) -> str:
        """
        Simula sinal de estratégia mean reversion
        
        Args:
            data: Dados históricos
            index: Índice atual
            
        Returns:
            Sinal ('buy', 'sell', 'hold')
        """
        if index < 20:
            return 'hold'
        
        # Calcula média e desvio padrão
        prices = [candle['close'] for candle in data[index-20:index]]
        mean_price = sum(prices) / len(prices)
        std_dev = (sum((p - mean_price) ** 2 for p in prices) / len(prices)) ** 0.5
        
        current_price = data[index]['close']
        
        # Bollinger Bands simplificado
        upper_band = mean_price + (2 * std_dev)
        lower_band = mean_price - (2 * std_dev)
        
        if current_price < lower_band:
            return 'buy'  # Preço muito baixo, espera reversão para cima
        elif current_price > upper_band:
            return 'sell'  # Preço muito alto, espera reversão para baixo
        else:
            return 'hold'
    
    async def run_full_backtest(self) -> Dict[str, Any]:
        """
        Executa backtest completo para todas as estratégias e símbolos
        
        Returns:
            Resultados consolidados
        """
        self.logger.info("Iniciando backtest completo...")
        
        all_results = {}
        
        for symbol in self.symbols:
            # Carrega dados históricos
            historical_data = await self.load_historical_data(
                symbol, self.start_date, self.end_date
            )
            
            symbol_results = {}
            
            for strategy in self.strategies:
                # Executa backtest da estratégia
                strategy_results = await self.run_strategy_backtest(
                    strategy, symbol, historical_data
                )
                symbol_results[strategy] = strategy_results
            
            all_results[symbol] = symbol_results
        
        # Gera resumo consolidado
        summary = self._generate_summary(all_results)
        
        final_results = {
            'config': self.config,
            'results': all_results,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info("Backtest completo finalizado!")
        return final_results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo dos resultados do backtest
        
        Args:
            results: Resultados por símbolo e estratégia
            
        Returns:
            Resumo consolidado
        """
        total_strategies = 0
        total_return_sum = 0
        best_strategy = None
        best_return = float('-inf')
        
        strategy_performance = {}
        
        for symbol, symbol_results in results.items():
            for strategy, strategy_results in symbol_results.items():
                total_strategies += 1
                return_pct = strategy_results['total_return_pct']
                total_return_sum += return_pct
                
                if return_pct > best_return:
                    best_return = return_pct
                    best_strategy = f"{strategy} ({symbol})"
                
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = []
                strategy_performance[strategy].append(return_pct)
        
        # Calcula médias por estratégia
        avg_performance = {}
        for strategy, returns in strategy_performance.items():
            avg_performance[strategy] = sum(returns) / len(returns)
        
        return {
            'total_strategies_tested': total_strategies,
            'average_return_pct': total_return_sum / total_strategies if total_strategies > 0 else 0,
            'best_strategy': best_strategy,
            'best_return_pct': best_return,
            'strategy_avg_performance': avg_performance,
            'symbols_tested': list(results.keys()),
            'strategies_tested': list(strategy_performance.keys())
        }
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """
        Salva resultados do backtest em arquivo
        
        Args:
            results: Resultados do backtest
            output_file: Caminho do arquivo de saída
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Resultados salvos em: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultados: {str(e)}")


async def main():
    """
    Função principal do script
    """
    parser = argparse.ArgumentParser(description='Executa backtest de estratégias de trading')
    parser.add_argument('--start-date', default='2024-01-01', help='Data de início (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2024-12-31', help='Data de fim (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000.0, help='Capital inicial')
    parser.add_argument('--symbols', nargs='+', default=['BTC/USDT'], help='Símbolos para testar')
    parser.add_argument('--strategies', nargs='+', default=['trend_following'], help='Estratégias para testar')
    parser.add_argument('--output', default='data/backtest_results.json', help='Arquivo de saída')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BACKTESTING DE ESTRATÉGIAS")
    print("Sistema de Trading de Criptomoedas")
    print("=" * 60)
    print(f"Período: {args.start_date} - {args.end_date}")
    print(f"Capital inicial: ${args.capital:,.2f}")
    print(f"Símbolos: {', '.join(args.symbols)}")
    print(f"Estratégias: {', '.join(args.strategies)}")
    print("=" * 60)
    
    # Configuração do backtest
    config = {
        'start_date': args.start_date,
        'end_date': args.end_date,
        'initial_capital': args.capital,
        'symbols': args.symbols,
        'strategies': args.strategies
    }
    
    try:
        # Executa backtest
        engine = BacktestEngine(config)
        results = await engine.run_full_backtest()
        
        # Salva resultados
        engine.save_results(results, args.output)
        
        # Exibe resumo
        summary = results['summary']
        print("\n📊 RESUMO DOS RESULTADOS:")
        print(f"Estratégias testadas: {summary['total_strategies_tested']}")
        print(f"Retorno médio: {summary['average_return_pct']:.2f}%")
        print(f"Melhor estratégia: {summary['best_strategy']}")
        print(f"Melhor retorno: {summary['best_return_pct']:.2f}%")
        
        print("\n📈 PERFORMANCE POR ESTRATÉGIA:")
        for strategy, avg_return in summary['strategy_avg_performance'].items():
            print(f"  {strategy}: {avg_return:.2f}%")
        
        print(f"\n💾 Resultados salvos em: {args.output}")
        print("\n🎉 Backtest concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro no backtest: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
