"""
Estratégia RSI (Relative Strength Index)
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
from collections import deque

from src.strategies.base_strategy import BaseStrategy
from src.utils.logger import obter_logger, log_performance


class EstrategiaRSI(BaseStrategy):
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
    Estratégia baseada no Índice de Força Relativa (RSI)
    
    O RSI é um oscilador de momentum que mede a velocidade e magnitude
    das mudanças de preço. Valores acima de 70 indicam sobrecompra,
    valores abaixo de 30 indicam sobrevenda.
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa a estratégia RSI
        
        Args:
            configuracao: Configurações da estratégia
        """
        super().__init__(configuracao)
        
        self.logger = obter_logger(__name__)
        
        # Parâmetros da estratégia
        self.periodo_rsi = configuracao.get('periodo_rsi', 14)
        self.nivel_sobrecompra = Decimal(str(configuracao.get('nivel_sobrecompra', 70)))
        self.nivel_sobrevenda = Decimal(str(configuracao.get('nivel_sobrevenda', 30)))
        self.simbolos = configuracao.get('simbolos', ['BTC/USDT'])
        self.volume_minimo = Decimal(str(configuracao.get('volume_minimo', 1000)))
        
        # Dados históricos para cálculo do RSI
        self.dados_historicos = {simbolo: deque(maxlen=self.periodo_rsi + 10) for simbolo in self.simbolos}
        self.valores_rsi = {simbolo: deque(maxlen=100) for simbolo in self.simbolos}
        
        # Estado da estratégia
        self.sinais_anteriores = {simbolo: 'NEUTRO' for simbolo in self.simbolos}
        self.ultima_analise = None
        
        # Estatísticas
        self.total_sinais_gerados = 0
        self.sinais_compra = 0
        self.sinais_venda = 0
        
        self.logger.info("📊 Estratégia RSI inicializada:")
        self.logger.info(f"  • Período RSI: {self.periodo_rsi}")
        self.logger.info(f"  • Sobrecompra: {self.nivel_sobrecompra}")
        self.logger.info(f"  • Sobrevenda: {self.nivel_sobrevenda}")
        self.logger.info(f"  • Símbolos: {', '.join(self.simbolos)}")
    
    @log_performance
    async def analisar(self, dados_mercado: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analisa o mercado usando RSI
        
        Args:
            dados_mercado: Dados atuais do mercado
            
        Returns:
            Lista de sinais de trading
        """
        sinais = []
        self.ultima_analise = datetime.now()
        
        try:
            for simbolo in self.simbolos:
                if simbolo not in dados_mercado:
                    continue
                
                dados_simbolo = dados_mercado[simbolo]
                
                # Validar dados
                if not self._validar_dados(dados_simbolo):
                    continue
                
                # Atualizar dados históricos
                await self._atualizar_dados_historicos(simbolo, dados_simbolo)
                
                # Verificar se temos dados suficientes
                if len(self.dados_historicos[simbolo]) < self.periodo_rsi:
                    continue
                
                # Calcular RSI
                rsi_atual = await self._calcular_rsi(simbolo)
                if rsi_atual is None:
                    continue
                
                # Armazenar valor RSI
                self.valores_rsi[simbolo].append(rsi_atual)
                
                # Gerar sinais baseados no RSI
                sinal = await self._gerar_sinal_rsi(simbolo, rsi_atual, dados_simbolo)
                if sinal:
                    sinais.append(sinal)
                    self.total_sinais_gerados += 1
                    
                    if sinal['acao'] == 'COMPRAR':
                        self.sinais_compra += 1
                    elif sinal['acao'] == 'VENDER':
                        self.sinais_venda += 1
        
        except Exception as e:
            self.logger.error(f"❌ Erro na análise RSI: {str(e)}")
        
        return sinais
    
    def _validar_dados(self, dados_simbolo: Dict[str, Any]) -> bool:
        """Valida os dados de entrada"""
        try:
            preco = dados_simbolo.get('preco')
            volume = dados_simbolo.get('volume_24h', 0)
            
            if preco is None or preco <= 0:
                return False
            
            if volume < float(self.volume_minimo):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _atualizar_dados_historicos(self, simbolo: str, dados_simbolo: Dict[str, Any]):
        """Atualiza dados históricos para o símbolo"""
        try:
            preco = Decimal(str(dados_simbolo['preco']))
            timestamp = dados_simbolo.get('timestamp', datetime.now())
            
            ponto_dados = {
                'preco': preco,
                'timestamp': timestamp
            }
            
            self.dados_historicos[simbolo].append(ponto_dados)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar dados históricos: {str(e)}")
    
    async def _calcular_rsi(self, simbolo: str) -> Optional[Decimal]:
        """
        Calcula o RSI para o símbolo
        
        Args:
            simbolo: Símbolo para calcular RSI
            
        Returns:
            Valor do RSI ou None se não for possível calcular
        """
        try:
            dados = list(self.dados_historicos[simbolo])
            
            if len(dados) < self.periodo_rsi + 1:
                return None
            
            # Calcular mudanças de preço
            mudancas = []
            for i in range(1, len(dados)):
                mudanca = dados[i]['preco'] - dados[i-1]['preco']
                mudancas.append(mudanca)
            
            # Separar ganhos e perdas
            ganhos = [max(mudanca, Decimal('0')) for mudanca in mudancas[-self.periodo_rsi:]]
            perdas = [abs(min(mudanca, Decimal('0'))) for mudanca in mudancas[-self.periodo_rsi:]]
            
            # Calcular médias
            media_ganhos = sum(ganhos) / len(ganhos) if ganhos else Decimal('0')
            media_perdas = sum(perdas) / len(perdas) if perdas else Decimal('0')
            
            # Evitar divisão por zero
            if media_perdas == 0:
                return Decimal('100')
            
            # Calcular RSI
            rs = media_ganhos / media_perdas
            rsi = Decimal('100') - (Decimal('100') / (Decimal('1') + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular RSI: {str(e)}")
            return None
    
    async def _gerar_sinal_rsi(self, simbolo: str, rsi: Decimal, dados_simbolo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Gera sinal baseado no valor do RSI
        
        Args:
            simbolo: Símbolo analisado
            rsi: Valor atual do RSI
            dados_simbolo: Dados do mercado
            
        Returns:
            Sinal de trading ou None
        """
        try:
            preco_atual = Decimal(str(dados_simbolo['preco']))
            volume = dados_simbolo.get('volume_24h', 0)
            
            sinal_anterior = self.sinais_anteriores[simbolo]
            acao = None
            motivo = ""
            confianca = 0.0
            
            # Lógica de sinais RSI
            if rsi <= self.nivel_sobrevenda and sinal_anterior != 'COMPRAR':
                # Condição de sobrevenda - sinal de compra
                acao = 'COMPRAR'
                motivo = f"RSI em sobrevenda: {rsi:.2f} <= {self.nivel_sobrevenda}"
                confianca = self._calcular_confianca_compra(rsi, volume)
                
            elif rsi >= self.nivel_sobrecompra and sinal_anterior != 'VENDER':
                # Condição de sobrecompra - sinal de venda
                acao = 'VENDER'
                motivo = f"RSI em sobrecompra: {rsi:.2f} >= {self.nivel_sobrecompra}"
                confianca = self._calcular_confianca_venda(rsi, volume)
            
            # Verificar se deve gerar sinal
            if acao and confianca >= 0.3:  # Confiança mínima de 30%
                self.sinais_anteriores[simbolo] = acao
                
                self.logger.info(f"📈 Sinal RSI gerado: {acao} {simbolo} - {motivo}")
                
                return {
                    'simbolo': simbolo,
                    'acao': acao,
                    'preco': float(preco_atual),
                    'timestamp': datetime.now(),
                    'estrategia': 'RSI',
                    'motivo': motivo,
                    'confianca': confianca,
                    'parametros': {
                        'rsi': float(rsi),
                        'periodo': self.periodo_rsi,
                        'sobrecompra': float(self.nivel_sobrecompra),
                        'sobrevenda': float(self.nivel_sobrevenda),
                        'volume': volume
                    }
                }
            
            # Resetar sinal anterior se RSI voltar ao meio
            if self.nivel_sobrevenda < rsi < self.nivel_sobrecompra:
                self.sinais_anteriores[simbolo] = 'NEUTRO'
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar sinal RSI: {str(e)}")
            return None
    
    def _calcular_confianca_compra(self, rsi: Decimal, volume: float) -> float:
        """Calcula confiança para sinal de compra"""
        try:
            # Confiança baseada em quão baixo está o RSI
            distancia_sobrevenda = max(0, float(self.nivel_sobrevenda - rsi))
            confianca_rsi = min(distancia_sobrevenda / 20.0, 0.5)  # Máximo 50%
            
            # Confiança baseada no volume
            volume_normalizado = min(volume / float(self.volume_minimo), 3.0)
            confianca_volume = min(volume_normalizado / 6.0, 0.3)  # Máximo 30%
            
            # Confiança total
            confianca_total = confianca_rsi + confianca_volume + 0.2  # Base 20%
            
            return min(confianca_total, 1.0)
            
        except Exception:
            return 0.3  # Confiança padrão
    
    def _calcular_confianca_venda(self, rsi: Decimal, volume: float) -> float:
        """Calcula confiança para sinal de venda"""
        try:
            # Confiança baseada em quão alto está o RSI
            distancia_sobrecompra = max(0, float(rsi - self.nivel_sobrecompra))
            confianca_rsi = min(distancia_sobrecompra / 20.0, 0.5)  # Máximo 50%
            
            # Confiança baseada no volume
            volume_normalizado = min(volume / float(self.volume_minimo), 3.0)
            confianca_volume = min(volume_normalizado / 6.0, 0.3)  # Máximo 30%
            
            # Confiança total
            confianca_total = confianca_rsi + confianca_volume + 0.2  # Base 20%
            
            return min(confianca_total, 1.0)
            
        except Exception:
            return 0.3  # Confiança padrão
    
    async def obter_status(self) -> Dict[str, Any]:
        """
        Obtém status atual da estratégia
        
        Returns:
            Dicionário com status da estratégia
        """
        try:
            # Calcular RSI atual para cada símbolo
            rsi_atual = {}
            dados_suficientes = {}
            
            for simbolo in self.simbolos:
                rsi = await self._calcular_rsi(simbolo)
                rsi_atual[simbolo] = float(rsi) if rsi else None
                
                dados_suficientes[simbolo] = {
                    'pontos_dados': len(self.dados_historicos[simbolo]),
                    'minimo_necessario': self.periodo_rsi,
                    'suficiente': len(self.dados_historicos[simbolo]) >= self.periodo_rsi
                }
            
            return {
                'nome': 'Estratégia RSI',
                'ativa': self.ativa,
                'simbolos_monitorados': len(self.simbolos),
                'periodo_rsi': self.periodo_rsi,
                'nivel_sobrecompra': float(self.nivel_sobrecompra),
                'nivel_sobrevenda': float(self.nivel_sobrevenda),
                'total_sinais_gerados': self.total_sinais_gerados,
                'sinais_compra': self.sinais_compra,
                'sinais_venda': self.sinais_venda,
                'ultima_analise': self.ultima_analise.isoformat() if self.ultima_analise else None,
                'rsi_atual': rsi_atual,
                'dados_suficientes': dados_suficientes,
                'sinais_anteriores': self.sinais_anteriores
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter status: {str(e)}")
            return {
                'nome': 'Estratégia RSI',
                'ativa': self.ativa,
                'erro': str(e)
            }
    
    async def obter_metricas_performance(self) -> Dict[str, Any]:
        """
        Obtém métricas de performance da estratégia
        
        Returns:
            Dicionário com métricas
        """
        try:
            return {
                'sinais_totais': self.total_sinais_gerados,
                'sinais_compra': self.sinais_compra,
                'sinais_venda': self.sinais_venda,
                'taxa_sinais_compra': (self.sinais_compra / max(self.total_sinais_gerados, 1)) * 100,
                'taxa_sinais_venda': (self.sinais_venda / max(self.total_sinais_gerados, 1)) * 100,
                'simbolos_ativos': len([s for s in self.simbolos if len(self.dados_historicos[s]) > 0]),
                'dados_historicos_total': sum(len(dados) for dados in self.dados_historicos.values()),
                'valores_rsi_armazenados': sum(len(rsi) for rsi in self.valores_rsi.values()),
                'ultima_atualizacao': self.ultima_analise.isoformat() if self.ultima_analise else None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter métricas: {str(e)}")
            return {'erro': str(e)}
    
    async def resetar_dados(self):
        """Reseta todos os dados da estratégia"""
        try:
            for simbolo in self.simbolos:
                self.dados_historicos[simbolo].clear()
                self.valores_rsi[simbolo].clear()
                self.sinais_anteriores[simbolo] = 'NEUTRO'
            
            self.total_sinais_gerados = 0
            self.sinais_compra = 0
            self.sinais_venda = 0
            self.ultima_analise = None
            
            self.logger.info("🔄 Dados da estratégia RSI resetados")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao resetar dados: {str(e)}")


# Configuração padrão da estratégia RSI
CONFIGURACAO_PADRAO_RSI = {
    'periodo_rsi': 14,
    'nivel_sobrecompra': 70,
    'nivel_sobrevenda': 30,
    'simbolos': ['BTC/USDT'],
    'volume_minimo': 1000,
    'ativa': True
}


def criar_estrategia_rsi(configuracao: Optional[Dict[str, Any]] = None) -> EstrategiaRSI:
    """
    Cria instância da estratégia RSI
    
    Args:
        configuracao: Configuração personalizada
        
    Returns:
        Instância da estratégia RSI
    """
    config = CONFIGURACAO_PADRAO_RSI.copy()
    if configuracao:
        config.update(configuracao)
    
    return EstrategiaRSI(config)


if __name__ == "__main__":
    # Teste da estratégia RSI
    import asyncio
    
    async def testar_estrategia_rsi():
        """Teste básico da estratégia RSI"""
        print("🧪 Testando Estratégia RSI...")
        
        # Criar estratégia
        estrategia = criar_estrategia_rsi({
            'periodo_rsi': 10,  # Período menor para teste
            'simbolos': ['BTC/USDT']
        })
        
        # Simular dados de mercado com tendência
        precos_teste = [
            50000, 49500, 49000, 48500, 48000,  # Queda (deve gerar RSI baixo)
            47500, 47000, 46500, 46000, 45500,  # Continuação da queda
            46000, 46500, 47000, 47500, 48000,  # Recuperação
            48500, 49000, 49500, 50000, 50500   # Alta
        ]
        
        sinais_gerados = []
        
        for i, preco in enumerate(precos_teste):
            dados_mercado = {
                'BTC/USDT': {
                    'preco': preco,
                    'volume_24h': 1500,
                    'timestamp': datetime.now()
                }
            }
            
            sinais = await estrategia.analisar(dados_mercado)
            sinais_gerados.extend(sinais)
            
            if sinais:
                print(f"📊 Passo {i+1}: Preço ${preco} - Sinal: {sinais[0]['acao']}")
        
        # Obter status final
        status = await estrategia.obter_status()
        print(f"\n📈 Resultado:")
        print(f"  • Sinais gerados: {status['total_sinais_gerados']}")
        print(f"  • Sinais de compra: {status['sinais_compra']}")
        print(f"  • Sinais de venda: {status['sinais_venda']}")
        print(f"  • RSI atual: {status['rsi_atual']['BTC/USDT']}")
        
        print("✅ Teste da estratégia RSI concluído!")
    
    # Executar teste
    asyncio.run(testar_estrategia_rsi())
