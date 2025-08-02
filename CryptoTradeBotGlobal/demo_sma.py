#!/usr/bin/env python3
"""
Demonstração da Estratégia SMA + Adaptador Binance
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent))

from src.utils.logger import setup_logger
from src.strategies.estrategia_sma_simples import EstrategiaSMASimples, CONFIGURACAO_PADRAO_SMA_SIMPLES
from src.adapters.binance_adapter import AdaptadorBinance, CONFIGURACAO_PADRAO_BINANCE


async def demonstrar_estrategia_sma():
    """
    Demonstra a integração da estratégia SMA com o adaptador Binance
    Executa uma simulação de paper trading com logs das operações
    """
    logger = setup_logger('demo_sma')
    
    try:
        logger.info("🎯 DEMONSTRAÇÃO: Estratégia SMA + Adaptador Binance")
        logger.info("=" * 60)
        
        # Configurar estratégia SMA
        config_sma = CONFIGURACAO_PADRAO_SMA_SIMPLES.copy()
        config_sma.update({
            'periodo_sma_rapida': 5,
            'periodo_sma_lenta': 10,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 500
        })
        
        # Configurar adaptador Binance
        config_binance = CONFIGURACAO_PADRAO_BINANCE.copy()
        config_binance.update({
            'saldo_inicial': 10000,
            'modo_simulacao': True
        })
        
        # Inicializar componentes
        logger.info("📊 Inicializando Estratégia SMA...")
        estrategia = EstrategiaSMASimples(config_sma)
        
        logger.info("🏦 Inicializando Adaptador Binance...")
        adaptador = AdaptadorBinance(config_binance)
        
        # Conectar adaptador
        if not await adaptador.conectar():
            logger.error("❌ Falha ao conectar adaptador")
            return False
        
        logger.info("✅ Componentes inicializados com sucesso!")
        
        # Simular dados de mercado e executar estratégia
        logger.info("🔄 Iniciando simulação de paper trading...")
        
        # Sequência de preços que deve gerar sinais
        sequencia_precos = [
            49000, 49100, 49200, 49300, 49400,  # Preparação
            49500, 49600, 49700, 49800, 49900,  # Construção
            50200, 50500, 50800, 51100, 51400,  # Alta (deve gerar sinal de compra)
            51300, 51000, 50700, 50400, 50100,  # Correção
            49800, 49500, 49200, 48900, 48600   # Baixa (pode gerar sinal de venda)
        ]
        
        ordens_executadas = []
        
        for i, preco in enumerate(sequencia_precos):
            # Simular dados de mercado
            dados_mercado = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1500,
                    'timestamp': datetime.now()
                }
            }
            
            # Analisar com estratégia SMA
            sinais = await estrategia.analisar(dados_mercado)
            
            # Executar sinais no adaptador
            for sinal in sinais:
                try:
                    # Determinar quantidade baseada no saldo
                    saldos = await adaptador.obter_saldo()
                    
                    if sinal['acao'] == 'COMPRAR':
                        # Usar 10% do saldo USDT
                        saldo_usdt = saldos.get('USDT', 0)
                        valor_ordem = saldo_usdt * 0.1
                        quantidade = valor_ordem / preco
                        
                        if quantidade > 0:
                            ordem = await adaptador.simular_ordem(
                                'BTC/USDT', 'BUY', quantidade, preco
                            )
                            ordens_executadas.append(ordem)
                            logger.info(f"🛒 COMPRA executada: {quantidade:.6f} BTC @ ${preco}")
                    
                    elif sinal['acao'] == 'VENDER':
                        # Vender 50% do BTC disponível
                        saldo_btc = saldos.get('BTC', 0)
                        quantidade = saldo_btc * 0.5
                        
                        if quantidade > 0:
                            ordem = await adaptador.simular_ordem(
                                'BTC/USDT', 'SELL', quantidade, preco
                            )
                            ordens_executadas.append(ordem)
                            logger.info(f"💸 VENDA executada: {quantidade:.6f} BTC @ ${preco}")
                
                except Exception as e:
                    logger.error(f"❌ Erro ao executar ordem: {str(e)}")
            
            # Log do progresso
            if i % 5 == 0:
                logger.info(f"📈 Progresso: {i+1}/{len(sequencia_precos)} - Preço: ${preco}")
            
            # Pequena pausa para simular tempo real
            await asyncio.sleep(0.1)
        
        # Relatório final
        logger.info("📊 RELATÓRIO FINAL DA SIMULAÇÃO")
        logger.info("=" * 60)
        
        # Estatísticas da estratégia
        status_estrategia = await estrategia.obter_status()
        logger.info(f"📈 Sinais gerados: {status_estrategia['total_sinais_gerados']}")
        logger.info(f"🛒 Sinais de compra: {status_estrategia['sinais_compra']}")
        logger.info(f"💸 Sinais de venda: {status_estrategia['sinais_venda']}")
        
        # Estatísticas do adaptador
        stats_adaptador = await adaptador.obter_estatisticas()
        logger.info(f"💰 Valor do portfólio: ${stats_adaptador['valor_portfolio']:.2f}")
        logger.info(f"📊 P&L: ${stats_adaptador['pnl']:.2f}")
        logger.info(f"🔄 Total de ordens: {stats_adaptador['total_ordens']}")
        logger.info(f"💹 Volume negociado: ${stats_adaptador['volume_total']:.2f}")
        
        # Saldos finais
        saldos_finais = await adaptador.obter_saldo()
        logger.info("💼 Saldos finais:")
        for moeda, saldo in saldos_finais.items():
            if saldo > 0:
                logger.info(f"  • {moeda}: {saldo}")
        
        # Desconectar
        await adaptador.desconectar()
        
        logger.info("✅ Demonstração concluída com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na demonstração: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        print("🎯 Iniciando demonstração da Estratégia SMA...")
        sucesso = asyncio.run(demonstrar_estrategia_sma())
        
        if sucesso:
            print("✅ Demonstração concluída com sucesso!")
        else:
            print("❌ Demonstração falhou!")
            
        sys.exit(0 if sucesso else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️ Demonstração interrompida")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro fatal: {str(e)}")
        sys.exit(1)
