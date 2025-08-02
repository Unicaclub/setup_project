"""
Testes para Estratégia RSI
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal

from src.strategies.estrategia_rsi import EstrategiaRSI, criar_estrategia_rsi


class TestEstrategiaRSI:
    """Testes para a estratégia RSI"""
    
    @pytest.fixture
    def estrategia_rsi(self):
        """Fixture para criar estratégia RSI de teste"""
        config = {
            'periodo_rsi': 5,  # Período menor para testes
            'nivel_sobrecompra': 70,
            'nivel_sobrevenda': 30,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 1000
        }
        return criar_estrategia_rsi(config)
    
    @pytest.mark.asyncio
    async def test_inicializacao_estrategia(self, estrategia_rsi):
        """Testa inicialização da estratégia RSI"""
        assert estrategia_rsi.periodo_rsi == 5
        assert estrategia_rsi.nivel_sobrecompra == Decimal('70')
        assert estrategia_rsi.nivel_sobrevenda == Decimal('30')
        assert 'BTC/USDT' in estrategia_rsi.simbolos
        assert estrategia_rsi.ativa is True
    
    @pytest.mark.asyncio
    async def test_validacao_dados_validos(self, estrategia_rsi):
        """Testa validação com dados válidos"""
        dados_validos = {
            'preco': 50000,
            'volume_24h': 2000,
            'timestamp': datetime.now()
        }
        
        assert estrategia_rsi._validar_dados(dados_validos) is True
    
    @pytest.mark.asyncio
    async def test_validacao_dados_invalidos(self, estrategia_rsi):
        """Testa validação com dados inválidos"""
        # Preço inválido
        dados_preco_zero = {
            'preco': 0,
            'volume_24h': 2000
        }
        assert estrategia_rsi._validar_dados(dados_preco_zero) is False
        
        # Volume baixo
        dados_volume_baixo = {
            'preco': 50000,
            'volume_24h': 500
        }
        assert estrategia_rsi._validar_dados(dados_volume_baixo) is False
        
        # Preço ausente
        dados_sem_preco = {
            'volume_24h': 2000
        }
        assert estrategia_rsi._validar_dados(dados_sem_preco) is False
    
    @pytest.mark.asyncio
    async def test_atualizacao_dados_historicos(self, estrategia_rsi):
        """Testa atualização de dados históricos"""
        dados_simbolo = {
            'preco': 50000,
            'volume_24h': 2000,
            'timestamp': datetime.now()
        }
        
        # Inicialmente vazio
        assert len(estrategia_rsi.dados_historicos['BTC/USDT']) == 0
        
        # Adicionar dados
        await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados_simbolo)
        
        # Verificar se foi adicionado
        assert len(estrategia_rsi.dados_historicos['BTC/USDT']) == 1
        assert estrategia_rsi.dados_historicos['BTC/USDT'][0]['preco'] == Decimal('50000')
    
    @pytest.mark.asyncio
    async def test_calculo_rsi_dados_insuficientes(self, estrategia_rsi):
        """Testa cálculo RSI com dados insuficientes"""
        # Adicionar apenas 3 pontos (menos que o período de 5)
        for i, preco in enumerate([50000, 50100, 50200]):
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # RSI deve retornar None
        rsi = await estrategia_rsi._calcular_rsi('BTC/USDT')
        assert rsi is None
    
    @pytest.mark.asyncio
    async def test_calculo_rsi_tendencia_alta(self, estrategia_rsi):
        """Testa cálculo RSI com tendência de alta"""
        # Preços em alta constante
        precos_alta = [50000, 50500, 51000, 51500, 52000, 52500]
        
        for preco in precos_alta:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        rsi = await estrategia_rsi._calcular_rsi('BTC/USDT')
        
        # RSI deve ser alto (próximo de 100) em tendência de alta
        assert rsi is not None
        assert rsi > Decimal('70')  # Deve estar em sobrecompra
    
    @pytest.mark.asyncio
    async def test_calculo_rsi_tendencia_baixa(self, estrategia_rsi):
        """Testa cálculo RSI com tendência de baixa"""
        # Preços em queda constante
        precos_baixa = [52000, 51500, 51000, 50500, 50000, 49500]
        
        for preco in precos_baixa:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        rsi = await estrategia_rsi._calcular_rsi('BTC/USDT')
        
        # RSI deve ser baixo (próximo de 0) em tendência de baixa
        assert rsi is not None
        assert rsi < Decimal('30')  # Deve estar em sobrevenda
    
    @pytest.mark.asyncio
    async def test_geracao_sinal_compra_sobrevenda(self, estrategia_rsi):
        """Testa geração de sinal de compra em sobrevenda"""
        # Criar condição de sobrevenda
        precos_baixa = [52000, 51000, 50000, 49000, 48000, 47000]
        
        for preco in precos_baixa:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise
        dados_mercado = {
            'BTC/USDT': {
                'preco': 47000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_rsi.analisar(dados_mercado)
        
        # Deve gerar sinal de compra
        assert len(sinais) > 0
        assert sinais[0]['acao'] == 'COMPRAR'
        assert sinais[0]['estrategia'] == 'RSI'
        assert 'sobrevenda' in sinais[0]['motivo'].lower()
    
    @pytest.mark.asyncio
    async def test_geracao_sinal_venda_sobrecompra(self, estrategia_rsi):
        """Testa geração de sinal de venda em sobrecompra"""
        # Criar condição de sobrecompra
        precos_alta = [47000, 48000, 49000, 50000, 51000, 52000]
        
        for preco in precos_alta:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise
        dados_mercado = {
            'BTC/USDT': {
                'preco': 52000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_rsi.analisar(dados_mercado)
        
        # Deve gerar sinal de venda
        assert len(sinais) > 0
        assert sinais[0]['acao'] == 'VENDER'
        assert sinais[0]['estrategia'] == 'RSI'
        assert 'sobrecompra' in sinais[0]['motivo'].lower()
    
    @pytest.mark.asyncio
    async def test_prevencao_sinais_duplicados(self, estrategia_rsi):
        """Testa prevenção de sinais duplicados"""
        # Criar condição de sobrevenda
        precos_baixa = [52000, 51000, 50000, 49000, 48000, 47000]
        
        for preco in precos_baixa:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 47000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        # Primeira análise - deve gerar sinal
        sinais1 = await estrategia_rsi.analisar(dados_mercado)
        assert len(sinais1) > 0
        assert sinais1[0]['acao'] == 'COMPRAR'
        
        # Segunda análise com mesmo preço - não deve gerar sinal duplicado
        sinais2 = await estrategia_rsi.analisar(dados_mercado)
        assert len(sinais2) == 0  # Não deve gerar sinal duplicado
    
    @pytest.mark.asyncio
    async def test_reset_sinal_zona_neutra(self, estrategia_rsi):
        """Testa reset de sinal quando RSI volta à zona neutra"""
        # Criar condição de sobrevenda
        precos_baixa = [52000, 51000, 50000, 49000, 48000, 47000]
        
        for preco in precos_baixa:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Gerar sinal de compra
        dados_mercado = {
            'BTC/USDT': {
                'preco': 47000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_rsi.analisar(dados_mercado)
        assert len(sinais) > 0
        assert estrategia_rsi.sinais_anteriores['BTC/USDT'] == 'COMPRAR'
        
        # Adicionar preços que levem RSI à zona neutra
        precos_neutros = [47500, 48000, 48500, 49000, 49500]
        
        for preco in precos_neutros:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Analisar com preço neutro
        dados_neutro = {
            'BTC/USDT': {
                'preco': 49500,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        await estrategia_rsi.analisar(dados_neutro)
        
        # Sinal anterior deve ser resetado para NEUTRO
        assert estrategia_rsi.sinais_anteriores['BTC/USDT'] == 'NEUTRO'
    
    @pytest.mark.asyncio
    async def test_calculo_confianca_compra(self, estrategia_rsi):
        """Testa cálculo de confiança para sinal de compra"""
        rsi_baixo = Decimal('20')  # Muito baixo
        volume_alto = 5000  # Volume alto
        
        confianca = estrategia_rsi._calcular_confianca_compra(rsi_baixo, volume_alto)
        
        # Confiança deve ser alta
        assert confianca > 0.5
        assert confianca <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculo_confianca_venda(self, estrategia_rsi):
        """Testa cálculo de confiança para sinal de venda"""
        rsi_alto = Decimal('80')  # Muito alto
        volume_alto = 5000  # Volume alto
        
        confianca = estrategia_rsi._calcular_confianca_venda(rsi_alto, volume_alto)
        
        # Confiança deve ser alta
        assert confianca > 0.5
        assert confianca <= 1.0
    
    @pytest.mark.asyncio
    async def test_multiplos_simbolos(self, estrategia_rsi):
        """Testa estratégia com múltiplos símbolos"""
        # Configurar estratégia com múltiplos símbolos
        config = {
            'periodo_rsi': 5,
            'simbolos': ['BTC/USDT', 'ETH/USDT'],
            'volume_minimo': 1000
        }
        estrategia_multi = criar_estrategia_rsi(config)
        
        # Adicionar dados para ambos os símbolos
        precos_btc = [50000, 49000, 48000, 47000, 46000, 45000]  # Baixa
        precos_eth = [3000, 3100, 3200, 3300, 3400, 3500]  # Alta
        
        for preco in precos_btc:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_multi._atualizar_dados_historicos('BTC/USDT', dados)
        
        for preco in precos_eth:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_multi._atualizar_dados_historicos('ETH/USDT', dados)
        
        # Analisar ambos os símbolos
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            },
            'ETH/USDT': {
                'preco': 3500,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_multi.analisar(dados_mercado)
        
        # Deve gerar sinais para ambos os símbolos
        assert len(sinais) == 2
        
        # BTC deve gerar sinal de compra (sobrevenda)
        sinal_btc = next(s for s in sinais if s['simbolo'] == 'BTC/USDT')
        assert sinal_btc['acao'] == 'COMPRAR'
        
        # ETH deve gerar sinal de venda (sobrecompra)
        sinal_eth = next(s for s in sinais if s['simbolo'] == 'ETH/USDT')
        assert sinal_eth['acao'] == 'VENDER'
    
    @pytest.mark.asyncio
    async def test_obter_status(self, estrategia_rsi):
        """Testa obtenção de status da estratégia"""
        # Adicionar alguns dados
        precos = [50000, 49000, 48000, 47000, 46000, 45000]
        
        for preco in precos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        status = await estrategia_rsi.obter_status()
        
        # Verificar campos do status
        assert status['nome'] == 'Estratégia RSI'
        assert status['ativa'] is True
        assert status['periodo_rsi'] == 5
        assert status['nivel_sobrecompra'] == 70.0
        assert status['nivel_sobrevenda'] == 30.0
        assert 'rsi_atual' in status
        assert 'dados_suficientes' in status
        assert status['dados_suficientes']['BTC/USDT']['suficiente'] is True
    
    @pytest.mark.asyncio
    async def test_obter_metricas_performance(self, estrategia_rsi):
        """Testa obtenção de métricas de performance"""
        # Gerar alguns sinais
        precos_baixa = [52000, 51000, 50000, 49000, 48000, 47000]
        
        for preco in precos_baixa:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 47000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        await estrategia_rsi.analisar(dados_mercado)
        
        metricas = await estrategia_rsi.obter_metricas_performance()
        
        # Verificar métricas
        assert 'sinais_totais' in metricas
        assert 'sinais_compra' in metricas
        assert 'sinais_venda' in metricas
        assert 'taxa_sinais_compra' in metricas
        assert 'simbolos_ativos' in metricas
        assert metricas['sinais_totais'] > 0
    
    @pytest.mark.asyncio
    async def test_resetar_dados(self, estrategia_rsi):
        """Testa reset de dados da estratégia"""
        # Adicionar dados e gerar sinais
        precos = [50000, 49000, 48000, 47000, 46000, 45000]
        
        for preco in precos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_rsi._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        await estrategia_rsi.analisar(dados_mercado)
        
        # Verificar que há dados
        assert len(estrategia_rsi.dados_historicos['BTC/USDT']) > 0
        assert estrategia_rsi.total_sinais_gerados > 0
        
        # Resetar dados
        await estrategia_rsi.resetar_dados()
        
        # Verificar que dados foram limpos
        assert len(estrategia_rsi.dados_historicos['BTC/USDT']) == 0
        assert len(estrategia_rsi.valores_rsi['BTC/USDT']) == 0
        assert estrategia_rsi.sinais_anteriores['BTC/USDT'] == 'NEUTRO'
        assert estrategia_rsi.total_sinais_gerados == 0
        assert estrategia_rsi.sinais_compra == 0
        assert estrategia_rsi.sinais_venda == 0
        assert estrategia_rsi.ultima_analise is None


# Testes de edge cases
class TestEstrategiaRSIEdgeCases:
    """Testes de casos extremos para estratégia RSI"""
    
    @pytest.mark.asyncio
    async def test_rsi_com_precos_identicos(self):
        """Testa RSI com preços idênticos (sem variação)"""
        config = {
            'periodo_rsi': 5,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_rsi(config)
        
        # Preços idênticos
        precos_identicos = [50000] * 10
        
        for preco in precos_identicos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados)
        
        # RSI deve ser 50 (neutro) ou próximo
        rsi = await estrategia._calcular_rsi('BTC/USDT')
        assert rsi is not None
        # Com preços idênticos, RSI pode ser indefinido, mas nossa implementação deve lidar com isso
    
    @pytest.mark.asyncio
    async def test_rsi_com_dados_extremos(self):
        """Testa RSI com dados extremos"""
        config = {
            'periodo_rsi': 5,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_rsi(config)
        
        # Preços extremamente altos
        precos_extremos = [1, 1000000, 1, 1000000, 1, 1000000]
        
        for preco in precos_extremos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados)
        
        # RSI deve ser calculado sem erros
        rsi = await estrategia._calcular_rsi('BTC/USDT')
        assert rsi is not None
        assert 0 <= rsi <= 100
    
    @pytest.mark.asyncio
    async def test_analise_sem_dados_mercado(self):
        """Testa análise sem dados de mercado"""
        config = {
            'periodo_rsi': 5,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_rsi(config)
        
        # Dados de mercado vazios
        dados_mercado = {}
        
        sinais = await estrategia.analisar(dados_mercado)
        
        # Não deve gerar sinais
        assert len(sinais) == 0
    
    @pytest.mark.asyncio
    async def test_analise_com_simbolo_inexistente(self):
        """Testa análise com símbolo não configurado"""
        config = {
            'periodo_rsi': 5,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_rsi(config)
        
        # Dados para símbolo não configurado
        dados_mercado = {
            'ETH/USDT': {
                'preco': 3000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia.analisar(dados_mercado)
        
        # Não deve gerar sinais
        assert len(sinais) == 0


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v"])
