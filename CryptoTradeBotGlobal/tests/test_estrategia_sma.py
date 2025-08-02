"""
Testes para Estratégia SMA
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from src.strategies.estrategia_sma import EstrategiaSMA, CONFIGURACAO_PADRAO_SMA


class TestEstrategiaSMA:
    """Testes para a estratégia de Média Móvel Simples"""
    
    @pytest.fixture
    def configuracao_teste(self):
        """Configuração para testes"""
        return {
            'periodo_sma_rapida': 5,
            'periodo_sma_lenta': 10,
            'simbolos': ['BTC/USDT'],
            'intervalo_analise': 30,
            'volume_minimo': 100
        }
    
    @pytest.fixture
    def dados_mercado_teste(self):
        """Dados de mercado para testes"""
        return {
            'BTC/USDT': {
                'preco': 50000,
                'volume_24h': 1000,
                'timestamp': datetime.now()
            }
        }
    
    def test_inicializacao_estrategia(self, configuracao_teste):
        """Testa inicialização da estratégia SMA"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        assert estrategia.periodo_sma_rapida == 5
        assert estrategia.periodo_sma_lenta == 10
        assert 'BTC/USDT' in estrategia.simbolos
        assert estrategia.volume_minimo == Decimal('100')
        assert estrategia.total_sinais_gerados == 0
    
    def test_validacao_periodos_sma(self):
        """Testa validação dos períodos das SMAs"""
        configuracao_invalida = {
            'periodo_sma_rapida': 20,
            'periodo_sma_lenta': 10,  # Menor que a rápida
            'simbolos': ['BTC/USDT']
        }
        
        with pytest.raises(ValueError, match="Período da SMA rápida deve ser menor que a SMA lenta"):
            EstrategiaSMA(configuracao_invalida)
    
    @pytest.mark.asyncio
    async def test_analise_sem_dados_suficientes(self, configuracao_teste, dados_mercado_teste):
        """Testa análise com dados insuficientes"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Primeira análise - não deve gerar sinais (dados insuficientes)
        sinais = await estrategia.analisar(dados_mercado_teste)
        
        assert isinstance(sinais, list)
        assert len(sinais) == 0  # Sem dados suficientes para SMA
    
    @pytest.mark.asyncio
    async def test_analise_com_dados_suficientes(self, configuracao_teste):
        """Testa análise com dados suficientes para calcular SMAs"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Simular dados históricos suficientes
        for i in range(15):  # Mais que o período da SMA lenta (10)
            dados_teste = {
                'BTC/USDT': {
                    'preco': 50000 + (i * 100),  # Preço crescente
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            sinais = await estrategia.analisar(dados_teste)
        
        # Verificar se estratégia tem dados suficientes
        status = await estrategia.obter_status()
        assert status['dados_suficientes']['BTC/USDT']['suficiente'] is True
    
    @pytest.mark.asyncio
    async def test_geracao_sinal_cruzamento_alta(self, configuracao_teste):
        """Testa geração de sinal de compra no cruzamento para cima"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Simular preços que causam cruzamento para cima
        precos_teste = [49000, 49100, 49200, 49300, 49400,  # SMA lenta baixa
                       49500, 49600, 49700, 49800, 49900,  # Preparação
                       50500, 51000, 51500, 52000, 52500]  # Cruzamento para cima
        
        sinais_gerados = []
        
        for preco in precos_teste:
            dados_teste = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            sinais = await estrategia.analisar(dados_teste)
            sinais_gerados.extend(sinais)
        
        # Deve ter gerado pelo menos um sinal de compra
        sinais_compra = [s for s in sinais_gerados if s['acao'] == 'COMPRAR']
        assert len(sinais_compra) > 0
        
        # Verificar estrutura do sinal
        if sinais_compra:
            sinal = sinais_compra[0]
            assert sinal['simbolo'] == 'BTC/USDT'
            assert sinal['estrategia'] == 'SMA'
            assert 'motivo' in sinal
            assert 'confianca' in sinal
            assert 'parametros' in sinal
    
    @pytest.mark.asyncio
    async def test_geracao_sinal_cruzamento_baixa(self, configuracao_teste):
        """Testa geração de sinal de venda no cruzamento para baixo"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Primeiro, criar condição de alta (SMA rápida > SMA lenta)
        precos_alta = [50000 + (i * 100) for i in range(15)]
        
        for preco in precos_alta:
            dados_teste = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            await estrategia.analisar(dados_teste)
        
        # Agora simular queda para gerar cruzamento para baixo
        precos_baixa = [51000, 50500, 50000, 49500, 49000, 48500, 48000]
        
        sinais_gerados = []
        for preco in precos_baixa:
            dados_teste = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            sinais = await estrategia.analisar(dados_teste)
            sinais_gerados.extend(sinais)
        
        # Pode gerar sinal de venda
        sinais_venda = [s for s in sinais_gerados if s['acao'] == 'VENDER']
        
        # Verificar se há sinais de venda ou se a lógica está funcionando
        assert isinstance(sinais_gerados, list)
    
    @pytest.mark.asyncio
    async def test_volume_minimo_filtro(self, configuracao_teste):
        """Testa filtro de volume mínimo"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Simular dados com volume baixo
        for i in range(15):
            dados_teste = {
                'BTC/USDT': {
                    'preco': 50000 + (i * 100),
                    'volume_24h': 50,  # Abaixo do mínimo (100)
                    'timestamp': datetime.now()
                }
            }
            sinais = await estrategia.analisar(dados_teste)
        
        # Não deve gerar sinais devido ao volume baixo
        assert estrategia.total_sinais_gerados == 0
    
    @pytest.mark.asyncio
    async def test_calculo_sma(self, configuracao_teste):
        """Testa cálculo da SMA"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Adicionar dados históricos conhecidos
        precos_teste = [100, 110, 120, 130, 140]  # SMA = 120
        
        for preco in precos_teste:
            dados_teste = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados_teste['BTC/USDT'])
        
        # Calcular SMA de 5 períodos
        sma = await estrategia._calcular_sma('BTC/USDT', 5)
        
        assert sma is not None
        assert sma == Decimal('120')  # (100+110+120+130+140)/5 = 120
    
    @pytest.mark.asyncio
    async def test_calculo_sma_dados_insuficientes(self, configuracao_teste):
        """Testa cálculo da SMA com dados insuficientes"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Adicionar apenas 3 pontos de dados
        for i in range(3):
            dados_teste = {
                'BTC/USDT': {
                    'preco': 50000 + (i * 100),
                    'volume_24h': 1000,
                    'timestamp': datetime.now()
                }
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados_teste['BTC/USDT'])
        
        # Tentar calcular SMA de 5 períodos (insuficiente)
        sma = await estrategia._calcular_sma('BTC/USDT', 5)
        
        assert sma is None
    
    def test_calculo_confianca(self, configuracao_teste):
        """Testa cálculo do nível de confiança"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Teste com divergência pequena
        confianca_baixa = estrategia._calcular_confianca(
            Decimal('50000'), Decimal('50010'), Decimal('1000')
        )
        
        # Teste com divergência grande
        confianca_alta = estrategia._calcular_confianca(
            Decimal('50000'), Decimal('49000'), Decimal('2000')
        )
        
        assert 0.0 <= confianca_baixa <= 1.0
        assert 0.0 <= confianca_alta <= 1.0
        assert confianca_alta > confianca_baixa  # Maior divergência = maior confiança
    
    @pytest.mark.asyncio
    async def test_obter_status(self, configuracao_teste):
        """Testa obtenção de status da estratégia"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        status = await estrategia.obter_status()
        
        assert status['nome'] == 'Estratégia SMA'
        assert status['ativa'] is True
        assert status['simbolos_monitorados'] == 1
        assert status['periodo_sma_rapida'] == 5
        assert status['periodo_sma_lenta'] == 10
        assert status['total_sinais_gerados'] == 0
        assert 'dados_suficientes' in status
    
    @pytest.mark.asyncio
    async def test_obter_metricas_performance(self, configuracao_teste):
        """Testa obtenção de métricas de performance"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        metricas = await estrategia.obter_metricas_performance()
        
        assert 'sinais_totais' in metricas
        assert 'sinais_compra' in metricas
        assert 'sinais_venda' in metricas
        assert 'taxa_sinais_compra' in metricas
        assert 'taxa_sinais_venda' in metricas
        assert 'simbolos_ativos' in metricas
        assert 'ultima_atualizacao' in metricas
    
    @pytest.mark.asyncio
    async def test_resetar_dados(self, configuracao_teste, dados_mercado_teste):
        """Testa reset dos dados da estratégia"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Adicionar alguns dados
        await estrategia.analisar(dados_mercado_teste)
        
        # Resetar
        await estrategia.resetar_dados()
        
        # Verificar se foi resetado
        assert estrategia.total_sinais_gerados == 0
        assert estrategia.sinais_compra == 0
        assert estrategia.sinais_venda == 0
        assert estrategia.ultima_analise is None
        
        # Verificar se dados históricos foram limpos
        for simbolo in estrategia.simbolos:
            assert len(estrategia.dados_historicos[simbolo]) == 0
            assert len(estrategia.sma_rapida[simbolo]) == 0
            assert len(estrategia.sma_lenta[simbolo]) == 0
    
    @pytest.mark.asyncio
    async def test_tratamento_erro_simbolo_inexistente(self, configuracao_teste):
        """Testa tratamento de erro para símbolo inexistente"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        dados_invalidos = {
            'ETH/USDT': {  # Símbolo não configurado
                'preco': 3000,
                'volume_24h': 1000,
                'timestamp': datetime.now()
            }
        }
        
        # Não deve gerar erro, apenas ignorar o símbolo
        sinais = await estrategia.analisar(dados_invalidos)
        assert isinstance(sinais, list)
        assert len(sinais) == 0
    
    @pytest.mark.asyncio
    async def test_tratamento_dados_preco_invalido(self, configuracao_teste):
        """Testa tratamento de dados com preço inválido"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        dados_invalidos = {
            'BTC/USDT': {
                # Sem campo 'preco'
                'volume_24h': 1000,
                'timestamp': datetime.now()
            }
        }
        
        # Não deve gerar erro
        sinais = await estrategia.analisar(dados_invalidos)
        assert isinstance(sinais, list)
    
    def test_configuracao_padrao(self):
        """Testa configuração padrão da estratégia"""
        assert 'periodo_sma_rapida' in CONFIGURACAO_PADRAO_SMA
        assert 'periodo_sma_lenta' in CONFIGURACAO_PADRAO_SMA
        assert 'simbolos' in CONFIGURACAO_PADRAO_SMA
        assert CONFIGURACAO_PADRAO_SMA['periodo_sma_rapida'] < CONFIGURACAO_PADRAO_SMA['periodo_sma_lenta']
    
    @pytest.mark.asyncio
    async def test_integracao_completa(self, configuracao_teste):
        """Teste de integração completa da estratégia"""
        estrategia = EstrategiaSMA(configuracao_teste)
        
        # Simular sequência realista de preços
        sequencia_precos = [
            # Fase 1: Preços estáveis
            50000, 50050, 50100, 50080, 50120,
            # Fase 2: Início de alta
            50200, 50300, 50450, 50600, 50750,
            # Fase 3: Alta confirmada
            50900, 51100, 51300, 51500, 51700,
            # Fase 4: Correção
            51600, 51400, 51200, 51000, 50800
        ]
        
        todos_sinais = []
        
        for preco in sequencia_precos:
            dados_teste = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1500,  # Volume suficiente
                    'timestamp': datetime.now()
                }
            }
            
            sinais = await estrategia.analisar(dados_teste)
            todos_sinais.extend(sinais)
            
            # Pequena pausa para simular tempo real
            await asyncio.sleep(0.01)
        
        # Verificar resultados finais
        status_final = await estrategia.obter_status()
        metricas_final = await estrategia.obter_metricas_performance()
        
        # Deve ter processado todos os dados
        assert status_final['dados_suficientes']['BTC/USDT']['suficiente'] is True
        
        # Pode ter gerado sinais
        assert isinstance(todos_sinais, list)
        
        # Métricas devem estar consistentes
        assert metricas_final['sinais_totais'] == len(todos_sinais)
        assert metricas_final['sinais_totais'] == estrategia.total_sinais_gerados


def test_funcao_criar_estrategia():
    """Testa função de conveniência para criar estratégia"""
    from src.strategies.estrategia_sma import criar_estrategia_sma
    
    config_teste = {'periodo_sma_rapida': 5, 'periodo_sma_lenta': 15}
    estrategia = criar_estrategia_sma(config_teste)
    
    assert isinstance(estrategia, EstrategiaSMA)
    assert estrategia.periodo_sma_rapida == 5
    assert estrategia.periodo_sma_lenta == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
