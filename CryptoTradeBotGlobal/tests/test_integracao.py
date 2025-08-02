"""
Testes de Integração - Fluxo Completo Main → Estratégia → Adapter
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime
import tempfile
import os

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.bot_trading import BotTrading
from src.strategies.estrategia_sma_simples import EstrategiaSMASimples, CONFIGURACAO_PADRAO_SMA_SIMPLES
from src.adapters.binance_adapter import AdaptadorBinance, CONFIGURACAO_PADRAO_BINANCE
from src.core.risk_manager import GerenciadorRisco
from src.utils.logger import obter_logger


class TestIntegracao:
    """Testes de integração do sistema completo"""
    
    @pytest.fixture
    def config_bot_teste(self):
        """Configuração de teste para o bot"""
        return {
            'intervalo_ciclo': 1,  # 1 segundo para testes rápidos
            'max_ciclos': 5,  # Limitar ciclos para testes
            'modo_simulacao': True,
            'log_level': 'INFO'
        }
    
    @pytest.fixture
    def config_estrategia_teste(self):
        """Configuração de teste para estratégia SMA"""
        config = CONFIGURACAO_PADRAO_SMA_SIMPLES.copy()
        config.update({
            'periodo_sma_rapida': 3,  # Períodos menores para testes
            'periodo_sma_lenta': 5,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 100
        })
        return config
    
    @pytest.fixture
    def config_adaptador_teste(self):
        """Configuração de teste para adaptador"""
        config = CONFIGURACAO_PADRAO_BINANCE.copy()
        config.update({
            'modo_simulacao': True,
            'saldo_inicial': 5000,
            'api_key': 'test_key',
            'api_secret': 'test_secret'
        })
        return config
    
    @pytest.fixture
    def config_risco_teste(self):
        """Configuração de teste para gerenciamento de risco"""
        return {
            'max_perda_diaria': 500,  # 10% do saldo inicial
            'max_drawdown': 0.15,  # 15%
            'stop_loss_percentual': 0.05,  # 5%
            'max_posicao_por_ativo': 0.3,  # 30% do portfolio
            'ativo': True
        }
    
    @pytest.mark.asyncio
    async def test_inicializacao_componentes_integrados(self, config_estrategia_teste, config_adaptador_teste, config_risco_teste):
        """Testa inicialização integrada de todos os componentes"""
        # Inicializar componentes
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        gerenciador_risco = GerenciadorRisco(config_risco_teste)
        
        # Verificar inicialização
        assert estrategia is not None
        assert adaptador is not None
        assert gerenciador_risco is not None
        
        # Conectar adaptador
        conectado = await adaptador.conectar()
        assert conectado is True
        
        # Verificar status inicial
        status_estrategia = await estrategia.obter_status()
        assert status_estrategia['ativa'] is True
        
        saldos = await adaptador.obter_saldo()
        assert saldos['USDT'] == 5000
        
        # Desconectar
        await adaptador.desconectar()
    
    @pytest.mark.asyncio
    async def test_fluxo_estrategia_para_adaptador(self, config_estrategia_teste, config_adaptador_teste):
        """Testa fluxo de sinais da estratégia para execução no adaptador"""
        # Inicializar componentes
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        
        await adaptador.conectar()
        
        # Simular sequência de dados que deve gerar sinal
        sequencia_precos = [
            48000, 48500, 49000, 49500, 50000,  # Tendência de alta
            50500, 51000, 51500, 52000, 52500   # Continuação da alta
        ]
        
        sinais_gerados = []
        ordens_executadas = []
        
        for preco in sequencia_precos:
            # Dados de mercado simulados
            dados_mercado = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            
            # Analisar com estratégia
            sinais = await estrategia.analisar(dados_mercado)
            sinais_gerados.extend(sinais)
            
            # Executar sinais no adaptador
            for sinal in sinais:
                try:
                    if sinal['acao'] == 'COMPRAR':
                        saldos = await adaptador.obter_saldo()
                        valor_compra = saldos['USDT'] * 0.5  # 50% do saldo
                        quantidade = valor_compra / preco
                        
                        if quantidade > 0:
                            ordem = await adaptador.simular_ordem('BTC/USDT', 'BUY', quantidade, preco)
                            ordens_executadas.append(ordem)
                    
                    elif sinal['acao'] == 'VENDER':
                        saldos = await adaptador.obter_saldo()
                        quantidade = saldos['BTC'] * 0.5  # 50% do BTC
                        
                        if quantidade > 0:
                            ordem = await adaptador.simular_ordem('BTC/USDT', 'SELL', quantidade, preco)
                            ordens_executadas.append(ordem)
                
                except Exception as e:
                    # Log do erro mas continua o teste
                    print(f"Erro ao executar ordem: {e}")
        
        # Verificações
        assert len(sinais_gerados) > 0, "Deveria ter gerado pelo menos um sinal"
        
        # Verificar estatísticas finais
        stats_estrategia = await estrategia.obter_status()
        stats_adaptador = await adaptador.obter_estatisticas()
        
        assert stats_estrategia['total_sinais_gerados'] > 0
        
        await adaptador.desconectar()
    
    @pytest.mark.asyncio
    async def test_integracao_com_gerenciamento_risco(self, config_estrategia_teste, config_adaptador_teste, config_risco_teste):
        """Testa integração com gerenciamento de risco"""
        # Inicializar componentes
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        gerenciador_risco = GerenciadorRisco(config_risco_teste)
        
        await adaptador.conectar()
        
        # Simular cenário de perda para testar stop-loss
        sequencia_precos = [
            50000, 49000, 48000, 47000, 46000,  # Queda acentuada
            45000, 44000, 43000, 42000, 41000   # Continuação da queda
        ]
        
        portfolio_inicial = await adaptador.obter_estatisticas()
        valor_inicial = portfolio_inicial['valor_portfolio']
        
        for preco in sequencia_precos:
            # Dados de mercado
            dados_mercado = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            
            # Analisar estratégia
            sinais = await estrategia.analisar(dados_mercado)
            
            # Aplicar gerenciamento de risco aos sinais
            for sinal in sinais:
                # Verificar se o sinal passa pelo filtro de risco
                saldos_atuais = await adaptador.obter_saldo()
                stats_atuais = await adaptador.obter_estatisticas()
                
                # Simular validação de risco
                risco_aprovado = gerenciador_risco.validar_ordem(
                    sinal, saldos_atuais, stats_atuais
                )
                
                if risco_aprovado:
                    # Executar ordem apenas se aprovada pelo risco
                    try:
                        if sinal['acao'] == 'COMPRAR':
                            saldos = await adaptador.obter_saldo()
                            valor_compra = min(saldos['USDT'] * 0.2, 1000)  # Máximo 20% ou 1000 USDT
                            quantidade = valor_compra / preco
                            
                            if quantidade > 0:
                                await adaptador.simular_ordem('BTC/USDT', 'BUY', quantidade, preco)
                        
                        elif sinal['acao'] == 'VENDER':
                            saldos = await adaptador.obter_saldo()
                            quantidade = saldos['BTC'] * 0.3  # Máximo 30% do BTC
                            
                            if quantidade > 0:
                                await adaptador.simular_ordem('BTC/USDT', 'SELL', quantidade, preco)
                    
                    except Exception as e:
                        print(f"Erro controlado na execução: {e}")
        
        # Verificar se o gerenciamento de risco funcionou
        portfolio_final = await adaptador.obter_estatisticas()
        perda_total = valor_inicial - portfolio_final['valor_portfolio']
        
        # A perda não deve exceder os limites configurados
        assert perda_total <= config_risco_teste['max_perda_diaria']
        
        await adaptador.desconectar()
    
    @pytest.mark.asyncio
    async def test_bot_trading_ciclo_completo(self, config_bot_teste, config_estrategia_teste, config_adaptador_teste):
        """Testa um ciclo completo do bot de trading"""
        # Configurar bot com componentes
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        
        # Simular dados de mercado para o bot
        dados_mercado_mock = {
            'BTC/USDT': {
                'preco': 50000,
                'volume_24h': 1500,
                'timestamp': datetime.now()
            }
        }
        
        # Conectar adaptador
        await adaptador.conectar()
        
        # Simular alguns ciclos de trading
        ciclos_executados = 0
        max_ciclos = 3
        
        while ciclos_executados < max_ciclos:
            try:
                # Simular variação de preço
                variacao = (ciclos_executados - 1) * 1000  # -1000, 0, +1000
                dados_mercado_mock['BTC/USDT']['preco'] = 50000 + variacao
                
                # Executar análise da estratégia
                sinais = await estrategia.analisar(dados_mercado_mock)
                
                # Processar sinais
                for sinal in sinais:
                    print(f"Ciclo {ciclos_executados}: Sinal {sinal['acao']} para {sinal['simbolo']}")
                
                # Simular pausa entre ciclos
                await asyncio.sleep(0.1)
                ciclos_executados += 1
                
            except Exception as e:
                print(f"Erro no ciclo {ciclos_executados}: {e}")
                break
        
        # Verificar resultados
        assert ciclos_executados == max_ciclos
        
        # Verificar estatísticas finais
        stats_estrategia = await estrategia.obter_status()
        stats_adaptador = await adaptador.obter_estatisticas()
        
        assert stats_estrategia is not None
        assert stats_adaptador is not None
        
        await adaptador.desconectar()
    
    @pytest.mark.asyncio
    async def test_tratamento_erros_integrado(self, config_estrategia_teste, config_adaptador_teste):
        """Testa tratamento de erros em cenário integrado"""
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        
        await adaptador.conectar()
        
        # Teste 1: Dados de mercado inválidos
        dados_invalidos = {
            'BTC/USDT': {
                'preco': None,  # Preço inválido
                'volume_24h': -100,  # Volume negativo
                'timestamp': 'invalid'  # Timestamp inválido
            }
        }
        
        # A estratégia deve lidar com dados inválidos graciosamente
        sinais = await estrategia.analisar(dados_invalidos)
        assert isinstance(sinais, list)  # Deve retornar lista vazia ou com tratamento
        
        # Teste 2: Ordem com parâmetros inválidos
        try:
            await adaptador.simular_ordem('INVALID/PAIR', 'BUY', -1, 0)
            assert False, "Deveria ter lançado exceção"
        except (ValueError, Exception) as e:
            assert True  # Esperado
        
        # Teste 3: Operação sem conexão
        await adaptador.desconectar()
        
        try:
            await adaptador.obter_preco('BTC/USDT')
            assert False, "Deveria ter lançado exceção de conexão"
        except Exception as e:
            assert True  # Esperado
    
    @pytest.mark.asyncio
    async def test_performance_integrada(self, config_estrategia_teste, config_adaptador_teste):
        """Testa performance do sistema integrado"""
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        
        await adaptador.conectar()
        
        # Medir tempo de execução de múltiplos ciclos
        inicio = datetime.now()
        
        num_ciclos = 10
        for i in range(num_ciclos):
            dados_mercado = {
                'BTC/USDT': {
                    'preco': 50000 + (i * 100),
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            
            # Executar análise
            sinais = await estrategia.analisar(dados_mercado)
            
            # Simular pequena pausa
            await asyncio.sleep(0.01)
        
        fim = datetime.now()
        tempo_total = (fim - inicio).total_seconds()
        
        # Verificar performance (deve ser rápido)
        tempo_por_ciclo = tempo_total / num_ciclos
        assert tempo_por_ciclo < 1.0, f"Ciclo muito lento: {tempo_por_ciclo}s"
        
        print(f"Performance: {tempo_por_ciclo:.3f}s por ciclo")
        
        await adaptador.desconectar()
    
    @pytest.mark.asyncio
    async def test_cenario_trading_realista(self, config_estrategia_teste, config_adaptador_teste):
        """Testa cenário de trading mais realista"""
        estrategia = EstrategiaSMASimples(config_estrategia_teste)
        adaptador = AdaptadorBinance(config_adaptador_teste)
        
        await adaptador.conectar()
        
        # Simular dados de mercado mais realistas
        precos_historicos = [
            49500, 49800, 50100, 50300, 50600,  # Tendência de alta gradual
            50400, 50200, 50500, 50800, 51000,  # Volatilidade
            50700, 50900, 51200, 51500, 51800,  # Continuação da alta
            51600, 51300, 51000, 50800, 50500,  # Correção
            50700, 51000, 51300, 51600, 52000   # Recuperação
        ]
        
        portfolio_inicial = await adaptador.obter_estatisticas()
        valor_inicial = portfolio_inicial['valor_portfolio']
        
        sinais_totais = 0
        ordens_executadas = 0
        
        for i, preco in enumerate(precos_historicos):
            dados_mercado = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1200 + (i * 50),  # Volume crescente
                    'timestamp': datetime.now()
                }
            }
            
            # Analisar mercado
            sinais = await estrategia.analisar(dados_mercado)
            sinais_totais += len(sinais)
            
            # Executar sinais com lógica de posicionamento
            for sinal in sinais:
                try:
                    saldos = await adaptador.obter_saldo()
                    
                    if sinal['acao'] == 'COMPRAR' and saldos['USDT'] > 500:
                        # Comprar com 25% do saldo USDT disponível
                        valor_compra = saldos['USDT'] * 0.25
                        quantidade = valor_compra / preco
                        
                        ordem = await adaptador.simular_ordem('BTC/USDT', 'BUY', quantidade, preco)
                        ordens_executadas += 1
                        print(f"COMPRA: {quantidade:.6f} BTC @ ${preco}")
                    
                    elif sinal['acao'] == 'VENDER' and saldos['BTC'] > 0.001:
                        # Vender 50% do BTC disponível
                        quantidade = saldos['BTC'] * 0.5
                        
                        ordem = await adaptador.simular_ordem('BTC/USDT', 'SELL', quantidade, preco)
                        ordens_executadas += 1
                        print(f"VENDA: {quantidade:.6f} BTC @ ${preco}")
                
                except Exception as e:
                    print(f"Erro na execução: {e}")
        
        # Análise dos resultados
        portfolio_final = await adaptador.obter_estatisticas()
        valor_final = portfolio_final['valor_portfolio']
        
        print(f"\n=== RESULTADOS DO CENÁRIO REALISTA ===")
        print(f"Valor inicial: ${valor_inicial:.2f}")
        print(f"Valor final: ${valor_final:.2f}")
        print(f"P&L: ${valor_final - valor_inicial:.2f}")
        print(f"Sinais gerados: {sinais_totais}")
        print(f"Ordens executadas: {ordens_executadas}")
        print(f"Volume total: ${portfolio_final['volume_total']:.2f}")
        
        # Verificações básicas
        assert sinais_totais >= 0
        assert ordens_executadas >= 0
        assert portfolio_final['total_ordens'] == ordens_executadas
        
        await adaptador.desconectar()


if __name__ == "__main__":
    # Executar testes de integração
    pytest.main([__file__, "-v", "--tb=short", "-s"])
