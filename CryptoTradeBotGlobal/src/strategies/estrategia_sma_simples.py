"""
Estratégia SMA Simplificada
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from collections import deque

from src.utils.logger import obter_logger


class EstrategiaSMASimples:
    """
    Estratégia de Trading baseada em Média Móvel Simples (SMA) - Versão Simplificada
    
    Esta estratégia utiliza duas médias móveis:
    - SMA Rápida (período menor): para sinais de entrada
    - SMA Lenta (período maior): para confirmação de tendência
    
    Sinais de Trading:
    - COMPRA: Quando SMA rápida cruza acima da SMA lenta
    - VENDA: Quando SMA rápida cruza abaixo da SMA lenta
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa a estratégia SMA
        
        Args:
            configuracao: Dicionário com configurações da estratégia
        """
        self.logger = obter_logger(__name__)
        
        # Configurações da estratégia
        self.periodo_sma_rapida = configuracao.get('periodo_sma_rapida', 5)
        self.periodo_sma_lenta = configuracao.get('periodo_sma_lenta', 10)
        self.simbolos = configuracao.get('simbolos', ['BTC/USDT'])
        self.volume_minimo = Decimal(str(configuracao.get('volume_minimo', 500)))
        
        # Validações
        if self.periodo_sma_rapida >= self.periodo_sma_lenta:
            raise ValueError("Período da SMA rápida deve ser menor que a SMA lenta")
        
        # Armazenamento de dados históricos
        self.dados_historicos: Dict[str, deque] = {}
        self.sma_rapida: Dict[str, deque] = {}
        self.sma_lenta: Dict[str, deque] = {}
        self.sinais_anteriores: Dict[str, str] = {}
        
        # Inicializar estruturas de dados para cada símbolo
        for simbolo in self.simbolos:
            self.dados_historicos[simbolo] = deque(maxlen=self.periodo_sma_lenta * 2)
            self.sma_rapida[simbolo] = deque(maxlen=50)
            self.sma_lenta[simbolo] = deque(maxlen=50)
            self.sinais_anteriores[simbolo] = 'NEUTRO'
        
        # Estatísticas da estratégia
        self.total_sinais_gerados = 0
        self.sinais_compra = 0
        self.sinais_venda = 0
        self.ultima_analise = None
        
        self.logger.info(f"📊 Estratégia SMA Simples inicializada:")
        self.logger.info(f"  • SMA Rápida: {self.periodo_sma_rapida} períodos")
        self.logger.info(f"  • SMA Lenta: {self.periodo_sma_lenta} períodos")
        self.logger.info(f"  • Símbolos: {', '.join(self.simbolos)}")
    
    async def analisar(self, dados_mercado: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analisa os dados de mercado e gera sinais de trading
        
        Args:
            dados_mercado: Dados de mercado atuais
            
        Returns:
            Lista de sinais de trading gerados
        """
        sinais = []
        self.ultima_analise = datetime.now()
        
        try:
            for simbolo in self.simbolos:
                if simbolo not in dados_mercado:
                    self.logger.warning(f"⚠️ Dados não disponíveis para {simbolo}")
                    continue
                
                dados_simbolo = dados_mercado[simbolo]
                
                # Atualizar dados históricos
                await self._atualizar_dados_historicos(simbolo, dados_simbolo)
                
                # Calcular SMAs
                sma_rapida_atual = await self._calcular_sma(simbolo, self.periodo_sma_rapida)
                sma_lenta_atual = await self._calcular_sma(simbolo, self.periodo_sma_lenta)
                
                if sma_rapida_atual is None or sma_lenta_atual is None:
                    continue
                
                # Armazenar SMAs calculadas
                self.sma_rapida[simbolo].append(sma_rapida_atual)
                self.sma_lenta[simbolo].append(sma_lenta_atual)
                
                # Gerar sinal de trading
                sinal = await self._gerar_sinal_trading(simbolo, sma_rapida_atual, sma_lenta_atual, dados_simbolo)
                
                if sinal:
                    sinais.append(sinal)
                    self.total_sinais_gerados += 1
                    
                    if sinal['acao'] == 'COMPRAR':
                        self.sinais_compra += 1
                    elif sinal['acao'] == 'VENDER':
                        self.sinais_venda += 1
                    
                    self.logger.info(f"📈 Sinal SMA gerado: {sinal['acao']} {simbolo} - {sinal['motivo']}")
        
        except Exception as e:
            self.logger.error(f"❌ Erro na análise SMA: {str(e)}")
        
        return sinais
    
    async def _atualizar_dados_historicos(self, simbolo: str, dados: Dict[str, Any]):
        """Atualiza os dados históricos para um símbolo"""
        try:
            # Extrair preço
            preco = None
            if 'preco' in dados:
                preco = Decimal(str(dados['preco']))
            elif 'last_price' in dados:
                preco = Decimal(str(dados['last_price']))
            elif 'close' in dados:
                preco = Decimal(str(dados['close']))
            
            if preco is None:
                self.logger.warning(f"⚠️ Preço não encontrado para {simbolo}")
                return
            
            # Adicionar aos dados históricos
            ponto_dados = {
                'preco': preco,
                'timestamp': datetime.now(),
                'volume': Decimal(str(dados.get('volume_24h', 0)))
            }
            
            self.dados_historicos[simbolo].append(ponto_dados)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar dados históricos para {simbolo}: {str(e)}")
    
    async def _calcular_sma(self, simbolo: str, periodo: int) -> Optional[Decimal]:
        """Calcula a Média Móvel Simples para um período específico"""
        try:
            dados = self.dados_historicos[simbolo]
            
            if len(dados) < periodo:
                return None
            
            # Pegar os últimos 'periodo' preços
            precos_recentes = [ponto['preco'] for ponto in list(dados)[-periodo:]]
            
            # Calcular média
            sma = sum(precos_recentes) / len(precos_recentes)
            
            return sma
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular SMA para {simbolo}: {str(e)}")
            return None
    
    async def _gerar_sinal_trading(self, simbolo: str, sma_rapida: Decimal, sma_lenta: Decimal, dados_mercado: Dict) -> Optional[Dict[str, Any]]:
        """Gera sinal de trading baseado no cruzamento das SMAs"""
        try:
            # Verificar se temos SMAs anteriores para detectar cruzamento
            if len(self.sma_rapida[simbolo]) < 2 or len(self.sma_lenta[simbolo]) < 2:
                return None
            
            # SMAs anteriores
            sma_rapida_anterior = self.sma_rapida[simbolo][-2]
            sma_lenta_anterior = self.sma_lenta[simbolo][-2]
            
            # Detectar cruzamentos
            cruzamento_alta = (sma_rapida_anterior <= sma_lenta_anterior and sma_rapida > sma_lenta)
            cruzamento_baixa = (sma_rapida_anterior >= sma_lenta_anterior and sma_rapida < sma_lenta)
            
            # Verificar volume mínimo
            volume_atual = Decimal(str(dados_mercado.get('volume_24h', 0)))
            if volume_atual < self.volume_minimo:
                return None
            
            sinal = None
            
            if cruzamento_alta and self.sinais_anteriores[simbolo] != 'COMPRAR':
                # Sinal de compra
                sinal = {
                    'simbolo': simbolo,
                    'acao': 'COMPRAR',
                    'preco': dados_mercado.get('preco', dados_mercado.get('last_price', 0)),
                    'timestamp': datetime.now(),
                    'motivo': f'Cruzamento alta: SMA{self.periodo_sma_rapida}({sma_rapida:.2f}) > SMA{self.periodo_sma_lenta}({sma_lenta:.2f})',
                    'confianca': self._calcular_confianca(sma_rapida, sma_lenta, volume_atual),
                    'estrategia': 'SMA',
                    'parametros': {
                        'sma_rapida': float(sma_rapida),
                        'sma_lenta': float(sma_lenta),
                        'periodo_rapida': self.periodo_sma_rapida,
                        'periodo_lenta': self.periodo_sma_lenta
                    }
                }
                self.sinais_anteriores[simbolo] = 'COMPRAR'
            
            elif cruzamento_baixa and self.sinais_anteriores[simbolo] != 'VENDER':
                # Sinal de venda
                sinal = {
                    'simbolo': simbolo,
                    'acao': 'VENDER',
                    'preco': dados_mercado.get('preco', dados_mercado.get('last_price', 0)),
                    'timestamp': datetime.now(),
                    'motivo': f'Cruzamento baixa: SMA{self.periodo_sma_rapida}({sma_rapida:.2f}) < SMA{self.periodo_sma_lenta}({sma_lenta:.2f})',
                    'confianca': self._calcular_confianca(sma_rapida, sma_lenta, volume_atual),
                    'estrategia': 'SMA',
                    'parametros': {
                        'sma_rapida': float(sma_rapida),
                        'sma_lenta': float(sma_lenta),
                        'periodo_rapida': self.periodo_sma_rapida,
                        'periodo_lenta': self.periodo_sma_lenta
                    }
                }
                self.sinais_anteriores[simbolo] = 'VENDER'
            
            return sinal
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar sinal para {simbolo}: {str(e)}")
            return None
    
    def _calcular_confianca(self, sma_rapida: Decimal, sma_lenta: Decimal, volume: Decimal) -> float:
        """Calcula nível de confiança do sinal"""
        try:
            # Calcular divergência percentual entre SMAs
            divergencia = abs(sma_rapida - sma_lenta) / sma_lenta * 100
            
            # Fator de volume (normalizado)
            fator_volume = min(float(volume / self.volume_minimo), 3.0) / 3.0
            
            # Confiança base pela divergência
            confianca_divergencia = min(float(divergencia) / 2.0, 1.0)
            
            # Confiança final combinando divergência e volume
            confianca_final = (confianca_divergencia * 0.7) + (fator_volume * 0.3)
            
            return min(max(confianca_final, 0.1), 1.0)
            
        except Exception:
            return 0.5
    
    async def obter_status(self) -> Dict[str, Any]:
        """Obtém status atual da estratégia"""
        status = {
            'nome': 'Estratégia SMA Simples',
            'ativa': True,
            'simbolos_monitorados': len(self.simbolos),
            'periodo_sma_rapida': self.periodo_sma_rapida,
            'periodo_sma_lenta': self.periodo_sma_lenta,
            'total_sinais_gerados': self.total_sinais_gerados,
            'sinais_compra': self.sinais_compra,
            'sinais_venda': self.sinais_venda,
            'ultima_analise': self.ultima_analise.isoformat() if self.ultima_analise else None,
            'dados_suficientes': {}
        }
        
        # Verificar se há dados suficientes para cada símbolo
        for simbolo in self.simbolos:
            dados_disponiveis = len(self.dados_historicos.get(simbolo, []))
            status['dados_suficientes'][simbolo] = {
                'pontos_dados': dados_disponiveis,
                'minimo_necessario': self.periodo_sma_lenta,
                'suficiente': dados_disponiveis >= self.periodo_sma_lenta
            }
        
        return status
    
    async def obter_metricas_performance(self) -> Dict[str, Any]:
        """Obtém métricas de performance da estratégia"""
        try:
            metricas = {
                'sinais_totais': self.total_sinais_gerados,
                'sinais_compra': self.sinais_compra,
                'sinais_venda': self.sinais_venda,
                'taxa_sinais_compra': (self.sinais_compra / max(self.total_sinais_gerados, 1)) * 100,
                'taxa_sinais_venda': (self.sinais_venda / max(self.total_sinais_gerados, 1)) * 100,
                'simbolos_ativos': len([s for s in self.simbolos if len(self.dados_historicos.get(s, [])) > 0]),
                'dados_historicos_total': sum(len(dados) for dados in self.dados_historicos.values()),
                'ultima_atualizacao': datetime.now().isoformat()
            }
            
            return metricas
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter métricas: {str(e)}")
            return {'erro': str(e)}


# Configuração padrão da estratégia
CONFIGURACAO_PADRAO_SMA_SIMPLES = {
    'periodo_sma_rapida': 5,
    'periodo_sma_lenta': 10,
    'simbolos': ['BTC/USDT'],
    'volume_minimo': 500,
    'nome': 'Estratégia SMA Simples',
    'descricao': 'Estratégia baseada em cruzamento de médias móveis simples'
}
