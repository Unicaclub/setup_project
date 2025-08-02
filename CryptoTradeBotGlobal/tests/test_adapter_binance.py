"""
Testes Avançados para o Adaptador Binance
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.adapters.binance_adapter import AdaptadorBinance, CONFIGURACAO_PADRAO_BINANCE
from src.core.exceptions import ErroConexao, ErroOrdem, ErroSaldo


class TestAdaptadorBinance:
    """Testes abrangentes para o Adaptador Binance"""
    
    @pytest.fixture
    def config_teste(self):
        """Configuração de teste para o adaptador"""
        config = CONFIGURACAO_PADRAO_BINANCE.copy()
        config.update({
            'modo_simulacao': True,
            'saldo_inicial': 10000,
            'api_key': 'test_key',
            'api_secret': 'test_secret'
        })
        return config
    
    @pytest.fixture
    def adaptador(self, config_teste):
        """Instância do adaptador para testes"""
        return AdaptadorBinance(config_teste)
    
    def test_inicializacao_basica(self, adaptador):
        """Testa inicialização básica do adaptador"""
        assert adaptador.nome == 'Binance'
        assert adaptador.modo_simulacao is True
        assert adaptador.saldo_inicial == Decimal('10000')
        assert adaptador.conectado is False
        assert len(adaptador.saldos) > 0
        assert 'USDT' in adaptador.saldos
    
    def test_inicializacao_com_config_invalida(self):
        """Testa inicialização com configuração inválida"""
        config_invalida = {
            'saldo_inicial': -1000,  # Saldo negativo
            'modo_simulacao': True
        }
        
        with pytest.raises(ValueError, match="Saldo inicial deve ser positivo"):
            AdaptadorBinance(config_invalida)
    
    @pytest.mark.asyncio
    async def test_conexao_simulacao(self, adaptador):
        """Testa conexão em modo simulação"""
        resultado = await adaptador.conectar()
        
        assert resultado is True
        assert adaptador.conectado is True
        assert adaptador.cliente_simulacao is not None
    
    @pytest.mark.asyncio
    async def test_desconexao(self, adaptador):
        """Testa desconexão do adaptador"""
        # Conectar primeiro
        await adaptador.conectar()
        assert adaptador.conectado is True
        
        # Desconectar
        await adaptador.desconectar()
        assert adaptador.conectado is False
    
    @pytest.mark.asyncio
    async def test_obter_saldo_inicial(self, adaptador):
        """Testa obtenção de saldos iniciais"""
        await adaptador.conectar()
        saldos = await adaptador.obter_saldo()
        
        assert isinstance(saldos, dict)
        assert 'USDT' in saldos
        assert saldos['USDT'] == Decimal('10000')
        assert 'BTC' in saldos
        assert saldos['BTC'] == Decimal('0')
    
    @pytest.mark.asyncio
    async def test_obter_preco_simulacao(self, adaptador):
        """Testa obtenção de preço em modo simulação"""
        await adaptador.conectar()
        
        preco = await adaptador.obter_preco('BTC/USDT')
        
        assert isinstance(preco, Decimal)
        assert preco > 0
        # Preço simulado deve estar em uma faixa realista
        assert 20000 <= float(preco) <= 100000
    
    @pytest.mark.asyncio
    async def test_obter_preco_simbolo_invalido(self, adaptador):
        """Testa obtenção de preço com símbolo inválido"""
        await adaptador.conectar()
        
        with pytest.raises(ValueError, match="Símbolo 'INVALID/PAIR' inválido ou não suportado."):
            await adaptador.obter_preco('INVALID/PAIR')
    
    @pytest.mark.asyncio
    async def test_simular_ordem_compra_valida(self, adaptador):
        """Testa simulação de ordem de compra válida"""
        await adaptador.conectar()
        
        # Ordem de compra de 0.1 BTC
        ordem = await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.1'), Decimal('50000'))
        
        assert ordem is not None
        assert ordem['simbolo'] == 'BTC/USDT'
        assert ordem['lado'] == 'BUY'
        assert ordem['quantidade'] == Decimal('0.1')
        assert ordem['preco'] == Decimal('50000')
        assert ordem['status'] == 'EXECUTADA'
        assert 'id' in ordem
        assert 'timestamp' in ordem
    
    @pytest.mark.asyncio
    async def test_simular_ordem_venda_valida(self, adaptador):
        """Testa simulação de ordem de venda válida"""
        await adaptador.conectar()
        
        # Primeiro, simular compra para ter BTC
        await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.1'), Decimal('50000'))
        
        # Agora vender parte do BTC
        ordem = await adaptador.simular_ordem('BTC/USDT', 'SELL', Decimal('0.05'), Decimal('51000'))
        
        assert ordem is not None
        assert ordem['simbolo'] == 'BTC/USDT'
        assert ordem['lado'] == 'SELL'
        assert ordem['quantidade'] == Decimal('0.05')
        assert ordem['preco'] == Decimal('51000')
        assert ordem['status'] == 'EXECUTADA'
    
    @pytest.mark.asyncio
    async def test_simular_ordem_saldo_insuficiente_compra(self, adaptador):
        """Testa ordem de compra com saldo insuficiente"""
        await adaptador.conectar()
        
        # Tentar comprar mais BTC do que o saldo permite
        with pytest.raises(ErroSaldo, match="Saldo insuficiente"):
            await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('1.0'), Decimal('50000'))  # 50k USDT necessários
    
    @pytest.mark.asyncio
    async def test_simular_ordem_saldo_insuficiente_venda(self, adaptador):
        """Testa ordem de venda com saldo insuficiente"""
        await adaptador.conectar()
        
        # Tentar vender BTC sem ter saldo
        with pytest.raises(ErroSaldo, match="Saldo insuficiente"):
            await adaptador.simular_ordem('BTC/USDT', 'SELL', Decimal('0.1'), Decimal('50000'))
    
    @pytest.mark.asyncio
    async def test_simular_ordem_parametros_invalidos(self, adaptador):
        """Testa ordem com parâmetros inválidos"""
        await adaptador.conectar()
        
        # Quantidade negativa
        with pytest.raises(ValueError, match="Quantidade da ordem deve ser positiva."):
            await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('-0.1'), Decimal('50000'))
        
        # Preço negativo
        with pytest.raises(ValueError, match="Preço da ordem deve ser positivo."):
            await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.1'), Decimal('-50000'))
        
        # Lado inválido
        with pytest.raises(ValueError, match="Lado da ordem deve ser 'BUY' ou 'SELL'."):
            await adaptador.simular_ordem('BTC/USDT', 'INVALID', Decimal('0.1'), Decimal('50000'))
    
    @pytest.mark.asyncio
    async def test_atualizacao_saldos_apos_ordens(self, adaptador):
        """Testa se os saldos são atualizados corretamente após ordens"""
        await adaptador.conectar()
        
        # Saldos iniciais
        saldos_iniciais = await adaptador.obter_saldo()
        usdt_inicial = saldos_iniciais['USDT']
        btc_inicial = saldos_iniciais['BTC']
        
        # Executar ordem de compra
        from decimal import Decimal
        preco = Decimal('50000')
        quantidade = Decimal('0.1')
        await adaptador.simular_ordem('BTC/USDT', 'BUY', quantidade, preco)

        # Verificar saldos após compra
        saldos_pos_compra = await adaptador.obter_saldo()

        # USDT deve diminuir
        assert saldos_pos_compra['USDT'] < usdt_inicial
        assert abs(saldos_pos_compra['USDT'] - (usdt_inicial - preco * quantidade)) < Decimal('0.01')

        # BTC deve aumentar
        assert saldos_pos_compra['BTC'] > btc_inicial
        assert abs(saldos_pos_compra['BTC'] - (btc_inicial + quantidade)) < Decimal('0.000001')
    
    @pytest.mark.asyncio
    async def test_obter_estatisticas_iniciais(self, adaptador):
        """Testa obtenção de estatísticas iniciais"""
        await adaptador.conectar()
        
        stats = await adaptador.obter_estatisticas()
        
        assert isinstance(stats, dict)
        assert 'valor_portfolio' in stats
        assert 'pnl' in stats
        assert 'total_ordens' in stats
        assert 'volume_total' in stats
        assert 'ordens_executadas' in stats
        assert 'ordens_canceladas' in stats
        
        # Valores iniciais
        assert stats['total_ordens'] == 0
        assert stats['volume_total'] == 0
        assert stats['pnl'] == 0
        assert stats['valor_portfolio'] == 10000  # Saldo inicial
    
    @pytest.mark.asyncio
    async def test_obter_estatisticas_apos_ordens(self, adaptador):
        """Testa estatísticas após execução de ordens"""
        await adaptador.conectar()
        
        # Executar algumas ordens
        await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.1'), Decimal('50000'))
        await adaptador.simular_ordem('BTC/USDT', 'SELL', Decimal('0.05'), Decimal('51000'))
        
        stats = await adaptador.obter_estatisticas()
        
        # Deve ter registrado as ordens
        assert stats['total_ordens'] == 2
        assert stats['ordens_executadas'] == 2
        assert stats['volume_total'] > 0
    
    @pytest.mark.asyncio
    async def test_operacao_sem_conexao(self, adaptador):
        """Testa operações sem estar conectado"""
        # Não conectar o adaptador
        
        with pytest.raises(ErroConexao, match="Adaptador não está conectado"):
            await adaptador.obter_preco('BTC/USDT')
        
        with pytest.raises(ErroConexao, match="Adaptador não está conectado"):
            await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.1'), Decimal('50000'))
        
        with pytest.raises(ErroConexao, match="Adaptador não está conectado"):
            await adaptador.obter_saldo()
    
    @pytest.mark.asyncio
    async def test_multiplas_ordens_sequenciais(self, adaptador):
        """Testa múltiplas ordens em sequência"""
        await adaptador.conectar()
        
        ordens = []
        
        # Executar várias ordens de compra pequenas
        for i in range(5):
            ordem = await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.01'), Decimal('50000') + i * 100)
            ordens.append(ordem)
        
        # Verificar que todas foram executadas
        assert len(ordens) == 5
        for ordem in ordens:
            assert ordem['status'] == 'EXECUTADA'
        
        # Verificar estatísticas
        stats = await adaptador.obter_estatisticas()
        assert stats['total_ordens'] == 5
        assert stats['ordens_executadas'] == 5
    
    def test_validacao_simbolo(self, adaptador):
        """Testa validação de símbolos"""
        # Símbolos válidos
        assert adaptador._validar_simbolo('BTC/USDT') is True
        assert adaptador._validar_simbolo('ETH/USDT') is True
        assert adaptador._validar_simbolo('BNB/BTC') is True
        
        # Símbolos inválidos
        assert adaptador._validar_simbolo('INVALID') is False
        assert adaptador._validar_simbolo('BTC-USDT') is False
        assert adaptador._validar_simbolo('') is False
        assert adaptador._validar_simbolo(None) is False
    
    @pytest.mark.asyncio
    async def test_cenario_trading_completo(self, adaptador):
        """Testa um cenário completo de trading"""
        await adaptador.conectar()
        
        # 1. Verificar saldo inicial
        saldos_iniciais = await adaptador.obter_saldo()
        from decimal import Decimal
        assert saldos_iniciais['USDT'] == Decimal('10000')
        assert saldos_iniciais['BTC'] == Decimal('0')
        
        # 2. Comprar BTC
        ordem_compra = await adaptador.simular_ordem('BTC/USDT', 'BUY', Decimal('0.2'), Decimal('50000'))
        assert ordem_compra['status'] == 'EXECUTADA'
        
        # 3. Verificar saldos após compra
        saldos_pos_compra = await adaptador.obter_saldo()
        assert saldos_pos_compra['BTC'] == Decimal('0.2')
        assert saldos_pos_compra['USDT'] == Decimal('0')  # 10000 - (0.2 * 50000) = 0
        
        # 4. Vender parte do BTC com lucro
        ordem_venda = await adaptador.simular_ordem('BTC/USDT', 'SELL', Decimal('0.1'), Decimal('52000'))
        assert ordem_venda['status'] == 'EXECUTADA'
        
        # 5. Verificar saldos finais
        saldos_finais = await adaptador.obter_saldo()
        assert saldos_finais['BTC'] == Decimal('0.1')  # 0.2 - 0.1
        assert saldos_finais['USDT'] == Decimal('5200')  # 0.1 * 52000
        
        # 6. Verificar estatísticas finais
        stats = await adaptador.obter_estatisticas()
        assert stats['total_ordens'] == 2
        assert stats['ordens_executadas'] == 2
        assert stats['volume_total'] == 15200  # 10000 + 5200
        
        # 7. Calcular P&L esperado
        valor_portfolio = saldos_finais['USDT'] + (saldos_finais['BTC'] * 52000)
        pnl_esperado = float(valor_portfolio - 10000)
        assert abs(stats['pnl'] - pnl_esperado) < 0.01


if __name__ == "__main__":
    # Executar testes específicos
    pytest.main([__file__, "-v", "--tb=short"])
