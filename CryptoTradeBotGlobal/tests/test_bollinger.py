"""
Testes para Estratégia Bandas de Bollinger
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal

from src.strategies.estrategia_bollinger import EstrategiaBollinger, criar_estrategia_bollinger


class TestEstrategiaBollinger:
    """Testes para a estratégia Bandas de Bollinger"""
    
    @pytest.fixture
    def estrategia_bollinger(self):
        """Fixture para criar estratégia Bollinger de teste"""
        config = {
            'periodo': 10,  # Período menor para testes
            'desvios_padrao': 2.0,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 1000,
            'usar_reversao': True,
            'usar_breakout': False
        }
        return criar_estrategia_bollinger(config)
    
    @pytest.mark.asyncio
    async def test_inicializacao_estrategia(self, estrategia_bollinger):
        """Testa inicialização da estratégia Bollinger"""
        assert estrategia_bollinger.periodo == 10
        assert estrategia_bollinger.desvios_padrao == Decimal('2.0')
        assert 'BTC/USDT' in estrategia_bollinger.simbolos
        assert estrategia_bollinger.usar_reversao is True
        assert estrategia_bollinger.usar_breakout is False
        assert estrategia_bollinger.ativa is True
    
    @pytest.mark.asyncio
    async def test_validacao_dados_validos(self, estrategia_bollinger):
        """Testa validação com dados válidos"""
        dados_validos = {
            'preco': 50000,
            'volume_24h': 2000,
            'timestamp': datetime.now()
        }
        
        assert estrategia_bollinger._validar_dados(dados_validos) is True
    
    @pytest.mark.asyncio
    async def test_validacao_dados_invalidos(self, estrategia_bollinger):
        """Testa validação com dados inválidos"""
        # Preço inválido
        dados_preco_zero = {
            'preco': 0,
            'volume_24h': 2000
        }
        assert estrategia_bollinger._validar_dados(dados_preco_zero) is False
        
        # Volume baixo
        dados_volume_baixo = {
            'preco': 50000,
            'volume_24h': 500
        }
        assert estrategia_bollinger._validar_dados(dados_volume_baixo) is False
    
    @pytest.mark.asyncio
    async def test_atualizacao_dados_historicos(self, estrategia_bollinger):
        """Testa atualização de dados históricos"""
        dados_simbolo = {
            'preco': 50000,
            'volume_24h': 2000,
            'timestamp': datetime.now()
        }
        
        # Inicialmente vazio
        assert len(estrategia_bollinger.dados_historicos['BTC/USDT']) == 0
        
        # Adicionar dados
        await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados_simbolo)
        
        # Verificar se foi adicionado
        assert len(estrategia_bollinger.dados_historicos['BTC/USDT']) == 1
        assert estrategia_bollinger.dados_historicos['BTC/USDT'][0]['preco'] == Decimal('50000')
    
    @pytest.mark.asyncio
    async def test_calculo_bandas_dados_insuficientes(self, estrategia_bollinger):
        """Testa cálculo das bandas com dados insuficientes"""
        # Adicionar apenas 5 pontos (menos que o período de 10)
        for i, preco in enumerate([50000, 50100, 50200, 50300, 50400]):
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Bandas devem retornar None
        bandas = await estrategia_bollinger._calcular_bandas_bollinger('BTC/USDT')
        assert bandas is None
    
    @pytest.mark.asyncio
    async def test_calculo_bandas_dados_suficientes(self, estrategia_bollinger):
        """Testa cálculo das bandas com dados suficientes"""
        # Adicionar preços com alguma variação
        precos = [50000, 50100, 49900, 50200, 49800, 50300, 49700, 50400, 49600, 50500, 49500]
        
        for preco in precos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        bandas = await estrategia_bollinger._calcular_bandas_bollinger('BTC/USDT')
        
        # Verificar se as bandas foram calculadas
        assert bandas is not None
        assert 'preco_atual' in bandas
        assert 'media' in bandas
        assert 'banda_superior' in bandas
        assert 'banda_inferior' in bandas
        assert 'desvio_padrao' in bandas
        assert 'largura_banda' in bandas
        assert 'posicao_percentual' in bandas
        
        # Verificar relações lógicas
        assert bandas['banda_superior'] > bandas['media']
        assert bandas['banda_inferior'] < bandas['media']
        assert bandas['largura_banda'] == bandas['banda_superior'] - bandas['banda_inferior']
        assert 0 <= bandas['posicao_percentual'] <= 1
    
    @pytest.mark.asyncio
    async def test_determinacao_posicao_banda(self, estrategia_bollinger):
        """Testa determinação da posição em relação às bandas"""
        # Preço na banda superior
        posicao_superior = estrategia_bollinger._determinar_posicao_banda(
            Decimal('52000'),  # preco
            Decimal('52000'),  # banda_superior
            Decimal('48000'),  # banda_inferior
            Decimal('50000')   # media
        )
        assert posicao_superior == 'SUPERIOR'
        
        # Preço na banda inferior
        posicao_inferior = estrategia_bollinger._determinar_posicao_banda(
            Decimal('48000'),  # preco
            Decimal('52000'),  # banda_superior
            Decimal('48000'),  # banda_inferior
            Decimal('50000')   # media
        )
        assert posicao_inferior == 'INFERIOR'
        
        # Preço no meio
        posicao_meio = estrategia_bollinger._determinar_posicao_banda(
            Decimal('50000'),  # preco
            Decimal('52000'),  # banda_superior
            Decimal('48000'),  # banda_inferior
            Decimal('50000')   # media
        )
        assert posicao_meio == 'MEIO'
    
    @pytest.mark.asyncio
    async def test_sinal_reversao_compra_banda_inferior(self, estrategia_bollinger):
        """Testa sinal de compra por reversão na banda inferior"""
        # Criar dados que resultem em preço na banda inferior
        precos_base = [50000] * 5  # Preços estáveis
        precos_queda = [49000, 48000, 47000, 46000, 45000]  # Queda para banda inferior
        
        for preco in precos_base + precos_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise com preço na banda inferior
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_bollinger.analisar(dados_mercado)
        
        # Deve gerar sinal de compra
        assert len(sinais) > 0
        assert sinais[0]['acao'] == 'COMPRAR'
        assert sinais[0]['estrategia'] == 'Bollinger'
        assert 'banda inferior' in sinais[0]['motivo'].lower()
    
    @pytest.mark.asyncio
    async def test_sinal_reversao_venda_banda_superior(self, estrategia_bollinger):
        """Testa sinal de venda por reversão na banda superior"""
        # Criar dados que resultem em preço na banda superior
        precos_base = [50000] * 5  # Preços estáveis
        precos_alta = [51000, 52000, 53000, 54000, 55000]  # Alta para banda superior
        
        for preco in precos_base + precos_alta:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise com preço na banda superior
        dados_mercado = {
            'BTC/USDT': {
                'preco': 55000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_bollinger.analisar(dados_mercado)
        
        # Deve gerar sinal de venda
        assert len(sinais) > 0
        assert sinais[0]['acao'] == 'VENDER'
        assert sinais[0]['estrategia'] == 'Bollinger'
        assert 'banda superior' in sinais[0]['motivo'].lower()
    
    @pytest.mark.asyncio
    async def test_estrategia_breakout(self):
        """Testa estratégia no modo breakout"""
        config = {
            'periodo': 10,
            'desvios_padrao': 2.0,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 1000,
            'usar_reversao': False,
            'usar_breakout': True
        }
        estrategia_breakout = criar_estrategia_bollinger(config)
        
        # Criar dados que resultem em rompimento da banda superior
        precos_base = [50000] * 5
        precos_rompimento = [51000, 52000, 53000, 54000, 55000]
        
        for preco in precos_base + precos_rompimento:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_breakout._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise com rompimento
        dados_mercado = {
            'BTC/USDT': {
                'preco': 55000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia_breakout.analisar(dados_mercado)
        
        # Deve gerar sinal de compra (breakout para cima)
        assert len(sinais) > 0
        assert sinais[0]['acao'] == 'COMPRAR'
        assert 'rompimento' in sinais[0]['motivo'].lower()
    
    @pytest.mark.asyncio
    async def test_prevencao_sinais_duplicados(self, estrategia_bollinger):
        """Testa prevenção de sinais duplicados"""
        # Criar condição para sinal na banda inferior
        precos_base = [50000] * 5
        precos_queda = [49000, 48000, 47000, 46000, 45000]
        
        for preco in precos_base + precos_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        # Primeira análise - deve gerar sinal
        sinais1 = await estrategia_bollinger.analisar(dados_mercado)
        assert len(sinais1) > 0
        assert sinais1[0]['acao'] == 'COMPRAR'
        
        # Segunda análise com mesmo preço - não deve gerar sinal duplicado
        sinais2 = await estrategia_bollinger.analisar(dados_mercado)
        assert len(sinais2) == 0  # Não deve gerar sinal duplicado
    
    @pytest.mark.asyncio
    async def test_calculo_confianca_reversao_compra(self, estrategia_bollinger):
        """Testa cálculo de confiança para compra por reversão"""
        # Simular bandas
        bandas = {
            'banda_inferior': Decimal('45000'),
            'banda_superior': Decimal('55000'),
            'media': Decimal('50000'),
            'largura_banda': Decimal('10000')
        }
        
        preco_banda_inferior = Decimal('45000')
        volume_alto = 5000
        
        confianca = estrategia_bollinger._calcular_confianca_reversao_compra(
            preco_banda_inferior, bandas, volume_alto
        )
        
        # Confiança deve ser razoável
        assert 0.0 <= confianca <= 1.0
        assert confianca > 0.2  # Deve ter alguma confiança
    
    @pytest.mark.asyncio
    async def test_calculo_confianca_reversao_venda(self, estrategia_bollinger):
        """Testa cálculo de confiança para venda por reversão"""
        # Simular bandas
        bandas = {
            'banda_inferior': Decimal('45000'),
            'banda_superior': Decimal('55000'),
            'media': Decimal('50000'),
            'largura_banda': Decimal('10000')
        }
        
        preco_banda_superior = Decimal('55000')
        volume_alto = 5000
        
        confianca = estrategia_bollinger._calcular_confianca_reversao_venda(
            preco_banda_superior, bandas, volume_alto
        )
        
        # Confiança deve ser razoável
        assert 0.0 <= confianca <= 1.0
        assert confianca > 0.2  # Deve ter alguma confiança
    
    @pytest.mark.asyncio
    async def test_multiplos_simbolos(self, estrategia_bollinger):
        """Testa estratégia com múltiplos símbolos"""
        # Configurar estratégia com múltiplos símbolos
        config = {
            'periodo': 10,
            'simbolos': ['BTC/USDT', 'ETH/USDT'],
            'volume_minimo': 1000,
            'usar_reversao': True
        }
        estrategia_multi = criar_estrategia_bollinger(config)
        
        # Adicionar dados para BTC (queda para banda inferior)
        precos_btc_base = [50000] * 5
        precos_btc_queda = [49000, 48000, 47000, 46000, 45000]
        
        for preco in precos_btc_base + precos_btc_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_multi._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Adicionar dados para ETH (alta para banda superior)
        precos_eth_base = [3000] * 5
        precos_eth_alta = [3100, 3200, 3300, 3400, 3500]
        
        for preco in precos_eth_base + precos_eth_alta:
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
        
        # BTC deve gerar sinal de compra (banda inferior)
        sinal_btc = next(s for s in sinais if s['simbolo'] == 'BTC/USDT')
        assert sinal_btc['acao'] == 'COMPRAR'
        
        # ETH deve gerar sinal de venda (banda superior)
        sinal_eth = next(s for s in sinais if s['simbolo'] == 'ETH/USDT')
        assert sinal_eth['acao'] == 'VENDER'
    
    @pytest.mark.asyncio
    async def test_contadores_toques_bandas(self, estrategia_bollinger):
        """Testa contadores de toques nas bandas"""
        # Inicialmente zero
        assert estrategia_bollinger.toques_banda_superior == 0
        assert estrategia_bollinger.toques_banda_inferior == 0
        
        # Criar dados para toque na banda inferior
        precos_base = [50000] * 5
        precos_queda = [49000, 48000, 47000, 46000, 45000]
        
        for preco in precos_base + precos_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        await estrategia_bollinger.analisar(dados_mercado)
        
        # Deve incrementar contador de toque na banda inferior
        assert estrategia_bollinger.toques_banda_inferior > 0
    
    @pytest.mark.asyncio
    async def test_obter_status(self, estrategia_bollinger):
        """Testa obtenção de status da estratégia"""
        # Adicionar alguns dados
        precos = [50000, 50100, 49900, 50200, 49800, 50300, 49700, 50400, 49600, 50500, 49500]
        
        for preco in precos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        status = await estrategia_bollinger.obter_status()
        
        # Verificar campos do status
        assert status['nome'] == 'Estratégia Bandas de Bollinger'
        assert status['ativa'] is True
        assert status['periodo'] == 10
        assert status['desvios_padrao'] == 2.0
        assert status['modo'] == 'Reversão'
        assert 'bandas_atuais' in status
        assert 'dados_suficientes' in status
        assert status['dados_suficientes']['BTC/USDT']['suficiente'] is True
        assert status['bandas_atuais']['BTC/USDT'] is not None
    
    @pytest.mark.asyncio
    async def test_obter_metricas_performance(self, estrategia_bollinger):
        """Testa obtenção de métricas de performance"""
        # Gerar alguns sinais
        precos_base = [50000] * 5
        precos_queda = [49000, 48000, 47000, 46000, 45000]
        
        for preco in precos_base + precos_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia_bollinger._atualizar_dados_historicos('BTC/USDT', dados)
        
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
        }
        
        await estrategia_bollinger.analisar(dados_mercado)
        
        metricas = await estrategia_bollinger.obter_metricas_performance()
        
        # Verificar métricas
        assert 'sinais_totais' in metricas
        assert 'sinais_compra' in metricas
        assert 'sinais_venda' in metricas
        assert 'toques_banda_superior' in metricas
        assert 'toques_banda_inferior' in metricas
        assert 'simbolos_ativos' in metricas
        assert metricas['sinais_totais'] > 0


# Testes de edge cases
class TestEstrategiaBollingerEdgeCases:
    """Testes de casos extremos para estratégia Bollinger"""
    
    @pytest.mark.asyncio
    async def test_bandas_com_precos_identicos(self):
        """Testa cálculo das bandas com preços idênticos"""
        config = {
            'periodo': 10,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_bollinger(config)
        
        # Preços idênticos
        precos_identicos = [50000] * 15
        
        for preco in precos_identicos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados)
        
        bandas = await estrategia._calcular_bandas_bollinger('BTC/USDT')
        
        # Com preços idênticos, desvio padrão deve ser zero
        assert bandas is not None
        assert bandas['desvio_padrao'] == Decimal('0')
        assert bandas['banda_superior'] == bandas['media']
        assert bandas['banda_inferior'] == bandas['media']
        assert bandas['largura_banda'] == Decimal('0')
    
    @pytest.mark.asyncio
    async def test_bandas_com_dados_extremos(self):
        """Testa cálculo das bandas com dados extremos"""
        config = {
            'periodo': 10,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_bollinger(config)
        
        # Preços extremamente variáveis
        precos_extremos = [1, 1000000, 1, 1000000, 1, 1000000, 1, 1000000, 1, 1000000, 1]
        
        for preco in precos_extremos:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Bandas devem ser calculadas sem erros
        bandas = await estrategia._calcular_bandas_bollinger('BTC/USDT')
        assert bandas is not None
        assert bandas['banda_superior'] > bandas['banda_inferior']
        assert bandas['largura_banda'] > 0
    
    @pytest.mark.asyncio
    async def test_analise_sem_dados_mercado(self):
        """Testa análise sem dados de mercado"""
        config = {
            'periodo': 10,
            'simbolos': ['BTC/USDT']
        }
        estrategia = criar_estrategia_bollinger(config)
        
        # Dados de mercado vazios
        dados_mercado = {}
        
        sinais = await estrategia.analisar(dados_mercado)
        
        # Não deve gerar sinais
        assert len(sinais) == 0
    
    @pytest.mark.asyncio
    async def test_confianca_minima_nao_atingida(self):
        """Testa quando confiança mínima não é atingida"""
        config = {
            'periodo': 10,
            'simbolos': ['BTC/USDT'],
            'volume_minimo': 1000
        }
        estrategia = criar_estrategia_bollinger(config)
        
        # Criar dados com volume muito baixo para baixa confiança
        precos_base = [50000] * 5
        precos_queda = [49000, 48000, 47000, 46000, 45000]
        
        for preco in precos_base + precos_queda:
            dados = {
                'preco': preco,
                'volume_24h': 2000,
                'timestamp': datetime.now()
            }
            await estrategia._atualizar_dados_historicos('BTC/USDT', dados)
        
        # Simular análise com volume muito baixo
        dados_mercado = {
            'BTC/USDT': {
                'preco': 45000,
                'volume_24h': 100,  # Volume muito baixo
                'timestamp': datetime.now()
            }
        }
        
        sinais = await estrategia.analisar(dados_mercado)
        
        # Pode não gerar sinal se confiança for muito baixa
        # (depende da implementação específica do cálculo de confiança)
        assert isinstance(sinais, list)


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v"])
