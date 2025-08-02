"""
Estratégia Bandas de Bollinger
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
from collections import deque
import math

from src.strategies.base_strategy import BaseStrategy
from src.utils.logger import obter_logger, log_performance


class EstrategiaBollinger(BaseStrategy):
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
    Estratégia baseada nas Bandas de Bollinger
    
    As Bandas de Bollinger consistem em uma média móvel simples (linha central)
    e duas bandas (superior e inferior) calculadas usando desvio padrão.
    Sinais são gerados quando o preço toca ou cruza as bandas.
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa a estratégia Bandas de Bollinger
        
        Args:
            configuracao: Configurações da estratégia
        """
        super().__init__(configuracao)
        
        self.logger = obter_logger(__name__)
        
        # Parâmetros da estratégia
        self.periodo = configuracao.get('periodo', 20)
        self.desvios_padrao = Decimal(str(configuracao.get('desvios_padrao', 2.0)))
        self.simbolos = configuracao.get('simbolos', ['BTC/USDT'])
        self.volume_minimo = Decimal(str(configuracao.get('volume_minimo', 1000)))
        
        # Configurações de sinal
        self.usar_reversao = configuracao.get('usar_reversao', True)  # Reversão à média
        self.usar_breakout = configuracao.get('usar_breakout', False)  # Rompimento das bandas
        self.percentual_banda = Decimal(str(configuracao.get('percentual_banda', 0.02)))  # 2%
        
        # Dados históricos
        self.dados_historicos = {simbolo: deque(maxlen=self.periodo + 10) for simbolo in self.simbolos}
        self.bandas_historicas = {simbolo: deque(maxlen=100) for simbolo in self.simbolos}
        
        # Estado da estratégia
        self.ativa = True  # Garante que a estratégia está ativa após inicialização
        self.sinais_anteriores = {simbolo: 'NEUTRO' for simbolo in self.simbolos}
        self.posicao_banda = {simbolo: 'MEIO' for simbolo in self.simbolos}  # SUPERIOR, INFERIOR, MEIO
        self.ultima_analise = None
        
        # Estatísticas
        self.total_sinais_gerados = 0
        self.sinais_compra = 0
        self.sinais_venda = 0
        self.toques_banda_superior = 0
        self.toques_banda_inferior = 0
        
        self.logger.info("📊 Estratégia Bandas de Bollinger inicializada:")
        self.logger.info(f"  • Período: {self.periodo}")
        self.logger.info(f"  • Desvios padrão: {self.desvios_padrao}")
        self.logger.info(f"  • Modo: {'Reversão' if self.usar_reversao else 'Breakout'}")
        self.logger.info(f"  • Símbolos: {', '.join(self.simbolos)}")
    
    @log_performance
    async def analisar(self, dados_mercado: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analisa o mercado usando Bandas de Bollinger
        
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
                if len(self.dados_historicos[simbolo]) < self.periodo:
                    continue
                
                # Calcular Bandas de Bollinger
                bandas = await self._calcular_bandas_bollinger(simbolo)
                if not bandas:
                    continue
                
                # Armazenar bandas históricas
                self.bandas_historicas[simbolo].append(bandas)
                
                # Gerar sinais baseados nas bandas
                sinal = await self._gerar_sinal_bollinger(simbolo, bandas, dados_simbolo)
                if sinal:
                    sinais.append(sinal)
                    self.total_sinais_gerados += 1
                    
                    if sinal['acao'] == 'COMPRAR':
                        self.sinais_compra += 1
                    elif sinal['acao'] == 'VENDER':
                        self.sinais_venda += 1
        
        except Exception as e:
            self.logger.error(f"❌ Erro na análise Bollinger: {str(e)}")
        
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
    
    async def _calcular_bandas_bollinger(self, simbolo: str) -> Optional[Dict[str, Decimal]]:
        """
        Calcula as Bandas de Bollinger para o símbolo
        
        Args:
            simbolo: Símbolo para calcular as bandas
            
        Returns:
            Dicionário com as bandas ou None se não for possível calcular
        """
        try:
            dados = list(self.dados_historicos[simbolo])
            
            if len(dados) < self.periodo:
                return None
            
            # Obter preços dos últimos períodos
            precos = [ponto['preco'] for ponto in dados[-self.periodo:]]
            
            # Calcular média móvel simples (linha central)
            media = sum(precos) / len(precos)
            
            # Calcular desvio padrão
            variancia = sum((preco - media) ** 2 for preco in precos) / len(precos)
            desvio_padrao = Decimal(str(math.sqrt(float(variancia))))
            
            # Calcular bandas
            banda_superior = media + (self.desvios_padrao * desvio_padrao)
            banda_inferior = media - (self.desvios_padrao * desvio_padrao)
            
            # Preço atual
            preco_atual = dados[-1]['preco']
            
            return {
                'preco_atual': preco_atual,
                'media': media,
                'banda_superior': banda_superior,
                'banda_inferior': banda_inferior,
                'desvio_padrao': desvio_padrao,
                'largura_banda': banda_superior - banda_inferior,
                'posicao_percentual': (preco_atual - banda_inferior) / (banda_superior - banda_inferior) if banda_superior != banda_inferior else Decimal('0.5')
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular Bandas de Bollinger: {str(e)}")
            return None
    
    async def _gerar_sinal_bollinger(self, simbolo: str, bandas: Dict[str, Decimal], dados_simbolo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Gera sinal baseado nas Bandas de Bollinger
        
        Args:
            simbolo: Símbolo analisado
            bandas: Dados das bandas calculadas
            dados_simbolo: Dados do mercado
            
        Returns:
            Sinal de trading ou None
        """
        try:
            preco_atual = bandas['preco_atual']
            banda_superior = bandas['banda_superior']
            banda_inferior = bandas['banda_inferior']
            media = bandas['media']
            volume = dados_simbolo.get('volume_24h', 0)
            
            sinal_anterior = self.sinais_anteriores[simbolo]
            posicao_anterior = self.posicao_banda[simbolo]
            
            acao = None
            motivo = ""
            confianca = 0.0
            
            # Determinar posição atual em relação às bandas
            posicao_atual = self._determinar_posicao_banda(preco_atual, banda_superior, banda_inferior, media)
            self.posicao_banda[simbolo] = posicao_atual
            
            # Estratégia de reversão à média (padrão)
            if self.usar_reversao:
                acao, motivo, confianca = await self._sinal_reversao(
                    simbolo, preco_atual, bandas, volume, sinal_anterior, posicao_atual, posicao_anterior
                )
            
            # Estratégia de breakout (alternativa)
            elif self.usar_breakout:
                acao, motivo, confianca = await self._sinal_breakout(
                    simbolo, preco_atual, bandas, volume, sinal_anterior, posicao_atual, posicao_anterior
                )
            
            # Verificar se deve gerar sinal
            if acao and confianca >= 0.3:  # Confiança mínima de 30%
                self.sinais_anteriores[simbolo] = acao
                
                self.logger.info(f"📈 Sinal Bollinger gerado: {acao} {simbolo} - {motivo}")
                
                return {
                    'simbolo': simbolo,
                    'acao': acao,
                    'preco': float(preco_atual),
                    'timestamp': datetime.now(),
                    'estrategia': 'Bollinger',
                    'motivo': motivo,
                    'confianca': confianca,
                    'parametros': {
                        'banda_superior': float(banda_superior),
                        'banda_inferior': float(banda_inferior),
                        'media': float(media),
                        'posicao_percentual': float(bandas['posicao_percentual']),
                        'largura_banda': float(bandas['largura_banda']),
                        'periodo': self.periodo,
                        'desvios_padrao': float(self.desvios_padrao),
                        'volume': volume
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar sinal Bollinger: {str(e)}")
            return None
    
    def _determinar_posicao_banda(self, preco: Decimal, banda_superior: Decimal, 
                                 banda_inferior: Decimal, media: Decimal) -> str:
        """Determina a posição do preço em relação às bandas"""
        try:
            margem = (banda_superior - banda_inferior) * self.percentual_banda
            
            if preco >= banda_superior - margem:
                return 'SUPERIOR'
            elif preco <= banda_inferior + margem:
                return 'INFERIOR'
            else:
                return 'MEIO'
                
        except Exception:
            return 'MEIO'
    
    async def _sinal_reversao(self, simbolo: str, preco: Decimal, bandas: Dict[str, Decimal], 
                            volume: float, sinal_anterior: str, posicao_atual: str, 
                            posicao_anterior: str) -> tuple:
        """Gera sinais de reversão à média"""
        try:
            acao = None
            motivo = ""
            confianca = 0.0
            
            # Sinal de compra: preço toca banda inferior
            if (posicao_atual == 'INFERIOR' and (posicao_anterior != 'INFERIOR' or sinal_anterior != 'COMPRAR')):
                self.toques_banda_inferior += 1
                acao = 'COMPRAR'
                motivo = f"Preço tocou banda inferior: ${preco:.2f} <= ${bandas['banda_inferior']:.2f}"
                confianca = self._calcular_confianca_reversao_compra(preco, bandas, volume)
            # Permitir sinal na primeira análise (quando posicao_anterior == 'MEIO' e sinal_anterior == 'NEUTRO')
            elif (posicao_atual == 'INFERIOR' and posicao_anterior == 'MEIO' and sinal_anterior == 'NEUTRO'):
                self.toques_banda_inferior += 1
                acao = 'COMPRAR'
                motivo = f"Primeira análise: preço tocou banda inferior: ${preco:.2f} <= ${bandas['banda_inferior']:.2f}"
                confianca = self._calcular_confianca_reversao_compra(preco, bandas, volume)
            # Sinal de venda: preço toca banda superior
            elif (posicao_atual == 'SUPERIOR' and (posicao_anterior != 'SUPERIOR' or sinal_anterior != 'VENDER')):
                self.toques_banda_superior += 1
                acao = 'VENDER'
                motivo = f"Preço tocou banda superior: ${preco:.2f} >= ${bandas['banda_superior']:.2f}"
                confianca = self._calcular_confianca_reversao_venda(preco, bandas, volume)
            elif (posicao_atual == 'SUPERIOR' and posicao_anterior == 'MEIO' and sinal_anterior == 'NEUTRO'):
                self.toques_banda_superior += 1
                acao = 'VENDER'
                motivo = f"Primeira análise: preço tocou banda superior: ${preco:.2f} >= ${bandas['banda_superior']:.2f}"
                confianca = self._calcular_confianca_reversao_venda(preco, bandas, volume)
            return acao, motivo, confianca
            
        except Exception as e:
            self.logger.error(f"❌ Erro no sinal de reversão: {str(e)}")
            return None, "", 0.0
    
    async def _sinal_breakout(self, simbolo: str, preco: Decimal, bandas: Dict[str, Decimal], 
                            volume: float, sinal_anterior: str, posicao_atual: str, 
                            posicao_anterior: str) -> tuple:
        """Gera sinais de breakout"""
        try:
            acao = None
            motivo = ""
            confianca = 0.0
            
            # Sinal de compra: rompimento da banda superior
            if (posicao_atual == 'SUPERIOR' and posicao_anterior != 'SUPERIOR' and 
                sinal_anterior != 'COMPRAR'):
                
                acao = 'COMPRAR'
                motivo = f"Rompimento da banda superior: ${preco:.2f} > ${bandas['banda_superior']:.2f}"
                confianca = self._calcular_confianca_breakout_compra(preco, bandas, volume)
                
            # Sinal de venda: rompimento da banda inferior
            elif (posicao_atual == 'INFERIOR' and posicao_anterior != 'INFERIOR' and 
                  sinal_anterior != 'VENDER'):
                
                acao = 'VENDER'
                motivo = f"Rompimento da banda inferior: ${preco:.2f} < ${bandas['banda_inferior']:.2f}"
                confianca = self._calcular_confianca_breakout_venda(preco, bandas, volume)
            
            return acao, motivo, confianca
            
        except Exception as e:
            self.logger.error(f"❌ Erro no sinal de breakout: {str(e)}")
            return None, "", 0.0
    
    def _calcular_confianca_reversao_compra(self, preco: Decimal, bandas: Dict[str, Decimal], volume: float) -> float:
        """Calcula confiança para sinal de compra por reversão"""
        try:
            # Confiança baseada na distância da banda inferior
            distancia_banda = abs(preco - bandas['banda_inferior'])
            largura_banda = bandas['largura_banda']
            confianca_posicao = max(0, 0.5 - float(distancia_banda / largura_banda))
            
            # Confiança baseada na largura das bandas (volatilidade)
            largura_normalizada = min(float(largura_banda / bandas['media']), 0.1)
            confianca_volatilidade = largura_normalizada * 3  # Máximo 30%
            
            # Confiança baseada no volume
            volume_normalizado = min(volume / float(self.volume_minimo), 3.0)
            confianca_volume = min(volume_normalizado / 10.0, 0.2)  # Máximo 20%
            
            # Confiança total
            confianca_total = confianca_posicao + confianca_volatilidade + confianca_volume
            
            return min(confianca_total, 1.0)
            
        except Exception:
            return 0.3  # Confiança padrão
    
    def _calcular_confianca_reversao_venda(self, preco: Decimal, bandas: Dict[str, Decimal], volume: float) -> float:
        """Calcula confiança para sinal de venda por reversão"""
        try:
            # Confiança baseada na distância da banda superior
            distancia_banda = abs(preco - bandas['banda_superior'])
            largura_banda = bandas['largura_banda']
            confianca_posicao = max(0, 0.5 - float(distancia_banda / largura_banda))
            
            # Confiança baseada na largura das bandas
            largura_normalizada = min(float(largura_banda / bandas['media']), 0.1)
            confianca_volatilidade = largura_normalizada * 3  # Máximo 30%
            
            # Confiança baseada no volume
            volume_normalizado = min(volume / float(self.volume_minimo), 3.0)
            confianca_volume = min(volume_normalizado / 10.0, 0.2)  # Máximo 20%
            
            # Confiança total
            confianca_total = confianca_posicao + confianca_volatilidade + confianca_volume
            
            return min(confianca_total, 1.0)
            
        except Exception:
            return 0.3  # Confiança padrão
    
    def _calcular_confianca_breakout_compra(self, preco: Decimal, bandas: Dict[str, Decimal], volume: float) -> float:
        """Calcula confiança para sinal de compra por breakout"""
        try:
            # Confiança baseada na força do rompimento
            distancia_rompimento = preco - bandas['banda_superior']
            largura_banda = bandas['largura_banda']
            confianca_rompimento = min(float(distancia_rompimento / largura_banda) * 2, 0.4)
            
            # Confiança baseada no volume (mais importante em breakouts)
            volume_normalizado = min(volume / float(self.volume_minimo), 5.0)
            confianca_volume = min(volume_normalizado / 10.0, 0.4)  # Máximo 40%
            
            # Confiança total
            confianca_total = confianca_rompimento + confianca_volume + 0.2  # Base 20%
            
            return min(confianca_total, 1.0)
            
        except Exception:
            return 0.3  # Confiança padrão
    
    def _calcular_confianca_breakout_venda(self, preco: Decimal, bandas: Dict[str, Decimal], volume: float) -> float:
        """Calcula confiança para sinal de venda por breakout"""
        try:
            # Confiança baseada na força do rompimento
            distancia_rompimento = bandas['banda_inferior'] - preco
            largura_banda = bandas['largura_banda']
            confianca_rompimento = min(float(distancia_rompimento / largura_banda) * 2, 0.4)
            
            # Confiança baseada no volume
            volume_normalizado = min(volume / float(self.volume_minimo), 5.0)
            confianca_volume = min(volume_normalizado / 10.0, 0.4)  # Máximo 40%
            
            # Confiança total
            confianca_total = confianca_rompimento + confianca_volume + 0.2  # Base 20%
            
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
            # Calcular bandas atuais para cada símbolo
            bandas_atuais = {}
            dados_suficientes = {}
            
            for simbolo in self.simbolos:
                bandas = await self._calcular_bandas_bollinger(simbolo)
                if bandas:
                    bandas_atuais[simbolo] = {
                        'preco_atual': float(bandas['preco_atual']),
                        'banda_superior': float(bandas['banda_superior']),
                        'banda_inferior': float(bandas['banda_inferior']),
                        'media': float(bandas['media']),
                        'posicao_percentual': float(bandas['posicao_percentual']),
                        'largura_banda': float(bandas['largura_banda'])
                    }
                else:
                    bandas_atuais[simbolo] = None
                
                dados_suficientes[simbolo] = {
                    'pontos_dados': len(self.dados_historicos[simbolo]),
                    'minimo_necessario': self.periodo,
                    'suficiente': len(self.dados_historicos[simbolo]) >= self.periodo
                }
            
            return {
                'nome': 'Estratégia Bandas de Bollinger',
                'ativa': self.ativa,
                'simbolos_monitorados': len(self.simbolos),
                'periodo': self.periodo,
                'desvios_padrao': float(self.desvios_padrao),
                'modo': 'Reversão' if self.usar_reversao else 'Breakout',
                'total_sinais_gerados': self.total_sinais_gerados,
                'sinais_compra': self.sinais_compra,
                'sinais_venda': self.sinais_venda,
                'toques_banda_superior': self.toques_banda_superior,
                'toques_banda_inferior': self.toques_banda_inferior,
                'ultima_analise': self.ultima_analise.isoformat() if self.ultima_analise else None,
                'bandas_atuais': bandas_atuais,
                'dados_suficientes': dados_suficientes,
                'posicao_banda': self.posicao_banda,
                'sinais_anteriores': self.sinais_anteriores
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter status: {str(e)}")
            return {
                'nome': 'Estratégia Bandas de Bollinger',
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
                'toques_banda_superior': self.toques_banda_superior,
                'toques_banda_inferior': self.toques_banda_inferior,
                'simbolos_ativos': len([s for s in self.simbolos if len(self.dados_historicos[s]) > 0]),
                'dados_historicos_total': sum(len(dados) for dados in self.dados_historicos.values()),
                'bandas_armazenadas': sum(len(bandas) for bandas in self.bandas_historicas.values()),
                'ultima_atualizacao': self.ultima_analise.isoformat() if self.ultima_analise else None
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter métricas: {str(e)}")
            return {'erro': str(e)}


# Configuração padrão da estratégia Bollinger
CONFIGURACAO_PADRAO_BOLLINGER = {
    'periodo': 20,
    'desvios_padrao': 2.0,
    'simbolos': ['BTC/USDT'],
    'volume_minimo': 1000,
    'usar_reversao': True,
    'usar_breakout': False,
    'percentual_banda': 0.02,
    'ativa': True
}


def criar_estrategia_bollinger(configuracao: Optional[Dict[str, Any]] = None) -> EstrategiaBollinger:
    """
    Cria instância da estratégia Bandas de Bollinger
    
    Args:
        configuracao: Configuração personalizada
        
    Returns:
        Instância da estratégia Bollinger
    """
    config = CONFIGURACAO_PADRAO_BOLLINGER.copy()
    if configuracao:
        config.update(configuracao)
    
    return EstrategiaBollinger(config)


if __name__ == "__main__":
    # Teste da estratégia Bollinger
    import asyncio
    
    async def testar_estrategia_bollinger():
        """Teste básico da estratégia Bollinger"""
        print("🧪 Testando Estratégia Bandas de Bollinger...")
        
        # Criar estratégia
        estrategia = criar_estrategia_bollinger({
            'periodo': 10,  # Período menor para teste
            'simbolos': ['BTC/USDT']
        })
        
        # Simular dados de mercado com volatilidade
        precos_teste = [
            50000, 50100, 50200, 50150, 50300,  # Movimento inicial
            50250, 50400, 50350, 50500, 50450,  # Estabelecer bandas
            50600, 50750, 50900, 51000, 51200,  # Movimento para cima
            51100, 50950, 50800, 50650, 50500,  # Correção
            50350, 50200, 50050, 49900, 49750,  # Queda
            49850, 49950, 50050, 50150, 50250   # Recuperação
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
        print(f"  • Toques banda superior: {status['toques_banda_superior']}")
        print(f"  • Toques banda inferior: {status['toques_banda_inferior']}")
        
        if status['bandas_atuais']['BTC/USDT']:
            bandas = status['bandas_atuais']['BTC/USDT']
            print(f"  • Banda superior: ${bandas['banda_superior']:.2f}")
            print(f"  • Média: ${bandas['media']:.2f}")
            print(f"  • Banda inferior: ${bandas['banda_inferior']:.2f}")
        
        print("✅ Teste da estratégia Bollinger concluído!")
    
    # Executar teste
    asyncio.run(testar_estrategia_bollinger())
