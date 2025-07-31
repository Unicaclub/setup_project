"""
Estratégia de Seguimento de Tendência
Implementação de estratégia baseada em médias móveis e indicadores de momentum
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal

from ..base_strategy import EstrategiaBase, SinalTrade, TipoSinal, DadosMercado


class EstrategiaSeguimentoTendencia(EstrategiaBase):
    """
    Estratégia de seguimento de tendência usando médias móveis
    
    Características:
    - Cruzamento de médias móveis (EMA rápida e lenta)
    - Confirmação com RSI e MACD
    - Stop loss dinâmico baseado em ATR
    - Take profit em múltiplos do risco
    """
    
    def __init__(self, parametros: Dict[str, Any] = None):
        """
        Inicializa a estratégia de seguimento de tendência
        
        Args:
            parametros: Parâmetros de configuração
        """
        parametros_padrao = {
            'periodo_ema_rapida': 12,
            'periodo_ema_lenta': 26,
            'periodo_rsi': 14,
            'periodo_atr': 14,
            'multiplicador_stop': 2.0,
            'multiplicador_take_profit': 3.0,
            'rsi_sobrecompra': 70,
            'rsi_sobrevenda': 30,
            'min_volume_relativo': 1.2,
            'min_forca_tendencia': 0.6
        }
        
        if parametros:
            parametros_padrao.update(parametros)
        
        super().__init__("Seguimento de Tendência", parametros_padrao)
        
        # Parâmetros específicos
        self.periodo_ema_rapida = self.parametros['periodo_ema_rapida']
        self.periodo_ema_lenta = self.parametros['periodo_ema_lenta']
        self.periodo_rsi = self.parametros['periodo_rsi']
        self.periodo_atr = self.parametros['periodo_atr']
        self.multiplicador_stop = self.parametros['multiplicador_stop']
        self.multiplicador_take_profit = self.parametros['multiplicador_take_profit']
        self.rsi_sobrecompra = self.parametros['rsi_sobrecompra']
        self.rsi_sobrevenda = self.parametros['rsi_sobrevenda']
        self.min_volume_relativo = self.parametros['min_volume_relativo']
        self.min_forca_tendencia = self.parametros['min_forca_tendencia']
        
        # Estado interno
        self.ultima_tendencia: Dict[str, str] = {}  # 'alta', 'baixa', 'lateral'
        self.historico_sinais_por_simbolo: Dict[str, List[SinalTrade]] = {}
    
    async def _inicializar_especifica(self):
        """Inicialização específica da estratégia"""
        self.logger.info("Inicializando estratégia de seguimento de tendência")
        self.logger.info(f"Parâmetros: EMA({self.periodo_ema_rapida}, {self.periodo_ema_lenta}), "
                        f"RSI({self.periodo_rsi}), ATR({self.periodo_atr})")
    
    async def _finalizar_especifica(self):
        """Finalização específica da estratégia"""
        self.logger.info("Finalizando estratégia de seguimento de tendência")
        self.ultima_tendencia.clear()
        self.historico_sinais_por_simbolo.clear()
    
    async def _analisar_especifica(self, dados_mercado: DadosMercado) -> Optional[SinalTrade]:
        """
        Análise específica da estratégia de seguimento de tendência
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Sinal de trading se gerado, None caso contrário
        """
        try:
            simbolo = dados_mercado.simbolo
            precos = dados_mercado.precos
            
            # Verificar se temos dados suficientes
            min_periodos = max(self.periodo_ema_lenta, self.periodo_rsi, self.periodo_atr) + 10
            if len(precos) < min_periodos:
                self.logger.debug(f"Dados insuficientes para {simbolo}: {len(precos)} < {min_periodos}")
                return None
            
            # Calcular indicadores
            indicadores = self._calcular_indicadores(precos, dados_mercado.volume)
            
            # Analisar tendência
            analise_tendencia = self._analisar_tendencia(indicadores, simbolo)
            
            # Verificar condições de entrada
            sinal = self._verificar_condicoes_entrada(
                simbolo, precos, indicadores, analise_tendencia
            )
            
            return sinal
            
        except Exception as e:
            self.logger.error(f"Erro na análise específica para {dados_mercado.simbolo}: {e}")
            return None
    
    def _calcular_indicadores(self, precos: pd.DataFrame, volume: pd.Series) -> Dict[str, pd.Series]:
        """
        Calcula todos os indicadores necessários
        
        Args:
            precos: DataFrame com dados OHLCV
            volume: Série com dados de volume
            
        Returns:
            Dicionário com indicadores calculados
        """
        indicadores = {}
        
        # Médias móveis exponenciais
        indicadores['ema_rapida'] = precos['close'].ewm(span=self.periodo_ema_rapida).mean()
        indicadores['ema_lenta'] = precos['close'].ewm(span=self.periodo_ema_lenta).mean()
        
        # RSI
        indicadores['rsi'] = self.calcular_rsi(precos['close'], self.periodo_rsi)
        
        # MACD
        macd, linha_sinal, histograma = self.calcular_macd(precos['close'])
        indicadores['macd'] = macd
        indicadores['macd_sinal'] = linha_sinal
        indicadores['macd_histograma'] = histograma
        
        # ATR (Average True Range)
        indicadores['atr'] = self._calcular_atr(precos, self.periodo_atr)
        
        # Volume relativo
        indicadores['volume_ma'] = volume.rolling(window=20).mean()
        indicadores['volume_relativo'] = volume / indicadores['volume_ma']
        
        # Força da tendência (baseada na distância entre EMAs)
        diferenca_ema = abs(indicadores['ema_rapida'] - indicadores['ema_lenta'])
        indicadores['forca_tendencia'] = diferenca_ema / precos['close']
        
        return indicadores
    
    def _calcular_atr(self, precos: pd.DataFrame, periodo: int) -> pd.Series:
        """
        Calcula Average True Range (ATR)
        
        Args:
            precos: DataFrame com dados OHLC
            periodo: Período para cálculo
            
        Returns:
            Série com valores de ATR
        """
        high_low = precos['high'] - precos['low']
        high_close_prev = abs(precos['high'] - precos['close'].shift(1))
        low_close_prev = abs(precos['low'] - precos['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=periodo).mean()
        
        return atr
    
    def _analisar_tendencia(self, indicadores: Dict[str, pd.Series], simbolo: str) -> Dict[str, Any]:
        """
        Analisa a tendência atual do mercado
        
        Args:
            indicadores: Dicionário com indicadores calculados
            simbolo: Símbolo sendo analisado
            
        Returns:
            Dicionário com análise da tendência
        """
        ema_rapida = indicadores['ema_rapida'].iloc[-1]
        ema_lenta = indicadores['ema_lenta'].iloc[-1]
        rsi = indicadores['rsi'].iloc[-1]
        macd = indicadores['macd'].iloc[-1]
        macd_sinal = indicadores['macd_sinal'].iloc[-1]
        forca_tendencia = indicadores['forca_tendencia'].iloc[-1]
        
        # Determinar direção da tendência
        if ema_rapida > ema_lenta:
            direcao = 'alta'
        elif ema_rapida < ema_lenta:
            direcao = 'baixa'
        else:
            direcao = 'lateral'
        
        # Verificar confirmação do MACD
        confirmacao_macd = macd > macd_sinal if direcao == 'alta' else macd < macd_sinal
        
        # Calcular força da tendência
        forca = min(forca_tendencia * 10, 1.0)  # Normalizar para 0-1
        
        # Verificar mudança de tendência
        tendencia_anterior = self.ultima_tendencia.get(simbolo, 'lateral')
        mudanca_tendencia = tendencia_anterior != direcao
        
        # Atualizar tendência atual
        self.ultima_tendencia[simbolo] = direcao
        
        return {
            'direcao': direcao,
            'forca': forca,
            'confirmacao_macd': confirmacao_macd,
            'mudanca_tendencia': mudanca_tendencia,
            'rsi': rsi,
            'ema_rapida': ema_rapida,
            'ema_lenta': ema_lenta
        }
    
    def _verificar_condicoes_entrada(self, simbolo: str, precos: pd.DataFrame, 
                                   indicadores: Dict[str, pd.Series], 
                                   analise_tendencia: Dict[str, Any]) -> Optional[SinalTrade]:
        """
        Verifica condições de entrada para gerar sinal
        
        Args:
            simbolo: Símbolo sendo analisado
            precos: DataFrame com dados de preços
            indicadores: Indicadores calculados
            analise_tendencia: Análise da tendência
            
        Returns:
            Sinal de trading se condições forem atendidas
        """
        preco_atual = Decimal(str(precos['close'].iloc[-1]))
        volume_relativo = indicadores['volume_relativo'].iloc[-1]
        atr = indicadores['atr'].iloc[-1]
        
        # Verificar condições básicas
        if analise_tendencia['forca'] < self.min_forca_tendencia:
            return None
        
        if volume_relativo < self.min_volume_relativo:
            return None
        
        # Verificar se houve mudança de tendência recente
        if not analise_tendencia['mudanca_tendencia']:
            return None
        
        # Verificar se não temos sinal recente para este símbolo
        if self._tem_sinal_recente(simbolo):
            return None
        
        # Determinar tipo de sinal baseado na tendência
        if analise_tendencia['direcao'] == 'alta':
            # Condições para sinal de compra
            if (analise_tendencia['confirmacao_macd'] and 
                analise_tendencia['rsi'] < self.rsi_sobrecompra):
                
                return self._criar_sinal_compra(
                    simbolo, preco_atual, atr, analise_tendencia
                )
        
        elif analise_tendencia['direcao'] == 'baixa':
            # Condições para sinal de venda
            if (analise_tendencia['confirmacao_macd'] and 
                analise_tendencia['rsi'] > self.rsi_sobrevenda):
                
                return self._criar_sinal_venda(
                    simbolo, preco_atual, atr, analise_tendencia
                )
        
        return None
    
    def _criar_sinal_compra(self, simbolo: str, preco_atual: Decimal, 
                           atr: float, analise_tendencia: Dict[str, Any]) -> SinalTrade:
        """
        Cria sinal de compra
        
        Args:
            simbolo: Símbolo
            preco_atual: Preço atual
            atr: Average True Range
            analise_tendencia: Análise da tendência
            
        Returns:
            Sinal de compra
        """
        # Calcular stop loss baseado em ATR
        stop_loss = preco_atual - Decimal(str(atr * self.multiplicador_stop))
        
        # Calcular take profit
        risco = preco_atual - stop_loss
        take_profit = preco_atual + (risco * Decimal(str(self.multiplicador_take_profit)))
        
        # Calcular confiança do sinal
        confianca = self._calcular_confianca_sinal(analise_tendencia, TipoSinal.COMPRA)
        
        sinal = SinalTrade(
            simbolo=simbolo,
            tipo=TipoSinal.COMPRA,
            forca=analise_tendencia['forca'],
            preco_entrada=preco_atual,
            stop_loss=stop_loss,
            take_profit=take_profit,
            razao_risco_retorno=self.multiplicador_take_profit,
            confianca=confianca,
            metadados={
                'estrategia': self.nome,
                'atr': atr,
                'rsi': analise_tendencia['rsi'],
                'ema_rapida': analise_tendencia['ema_rapida'],
                'ema_lenta': analise_tendencia['ema_lenta'],
                'direcao_tendencia': analise_tendencia['direcao']
            }
        )
        
        # Adicionar ao histórico
        if simbolo not in self.historico_sinais_por_simbolo:
            self.historico_sinais_por_simbolo[simbolo] = []
        self.historico_sinais_por_simbolo[simbolo].append(sinal)
        
        return sinal
    
    def _criar_sinal_venda(self, simbolo: str, preco_atual: Decimal, 
                          atr: float, analise_tendencia: Dict[str, Any]) -> SinalTrade:
        """
        Cria sinal de venda
        
        Args:
            simbolo: Símbolo
            preco_atual: Preço atual
            atr: Average True Range
            analise_tendencia: Análise da tendência
            
        Returns:
            Sinal de venda
        """
        # Calcular stop loss baseado em ATR
        stop_loss = preco_atual + Decimal(str(atr * self.multiplicador_stop))
        
        # Calcular take profit
        risco = stop_loss - preco_atual
        take_profit = preco_atual - (risco * Decimal(str(self.multiplicador_take_profit)))
        
        # Calcular confiança do sinal
        confianca = self._calcular_confianca_sinal(analise_tendencia, TipoSinal.VENDA)
        
        sinal = SinalTrade(
            simbolo=simbolo,
            tipo=TipoSinal.VENDA,
            forca=analise_tendencia['forca'],
            preco_entrada=preco_atual,
            stop_loss=stop_loss,
            take_profit=take_profit,
            razao_risco_retorno=self.multiplicador_take_profit,
            confianca=confianca,
            metadados={
                'estrategia': self.nome,
                'atr': atr,
                'rsi': analise_tendencia['rsi'],
                'ema_rapida': analise_tendencia['ema_rapida'],
                'ema_lenta': analise_tendencia['ema_lenta'],
                'direcao_tendencia': analise_tendencia['direcao']
            }
        )
        
        # Adicionar ao histórico
        if simbolo not in self.historico_sinais_por_simbolo:
            self.historico_sinais_por_simbolo[simbolo] = []
        self.historico_sinais_por_simbolo[simbolo].append(sinal)
        
        return sinal
    
    def _calcular_confianca_sinal(self, analise_tendencia: Dict[str, Any], 
                                 tipo_sinal: TipoSinal) -> float:
        """
        Calcula a confiança do sinal baseada em múltiplos fatores
        
        Args:
            analise_tendencia: Análise da tendência
            tipo_sinal: Tipo do sinal
            
        Returns:
            Confiança do sinal (0-1)
        """
        fatores_confianca = []
        
        # Força da tendência
        fatores_confianca.append(analise_tendencia['forca'])
        
        # Confirmação do MACD
        if analise_tendencia['confirmacao_macd']:
            fatores_confianca.append(0.8)
        else:
            fatores_confianca.append(0.3)
        
        # RSI não em extremos
        rsi = analise_tendencia['rsi']
        if tipo_sinal == TipoSinal.COMPRA:
            if rsi < 50:
                fatores_confianca.append(0.8)
            else:
                fatores_confianca.append(0.5)
        else:  # VENDA
            if rsi > 50:
                fatores_confianca.append(0.8)
            else:
                fatores_confianca.append(0.5)
        
        # Mudança de tendência
        if analise_tendencia['mudanca_tendencia']:
            fatores_confianca.append(0.9)
        else:
            fatores_confianca.append(0.6)
        
        # Calcular média ponderada
        confianca = sum(fatores_confianca) / len(fatores_confianca)
        return min(confianca, 1.0)
    
    def _tem_sinal_recente(self, simbolo: str, horas: int = 4) -> bool:
        """
        Verifica se há sinal recente para o símbolo
        
        Args:
            simbolo: Símbolo a verificar
            horas: Número de horas para considerar como recente
            
        Returns:
            True se há sinal recente
        """
        if simbolo not in self.historico_sinais_por_simbolo:
            return False
        
        tempo_limite = time.time() - (horas * 3600)
        sinais_recentes = [
            s for s in self.historico_sinais_por_simbolo[simbolo]
            if s.timestamp > tempo_limite
        ]
        
        return len(sinais_recentes) > 0
    
    def _validar_parametros_especificos(self) -> bool:
        """
        Validação específica de parâmetros da estratégia
        
        Returns:
            True se parâmetros específicos são válidos
        """
        try:
            # Validar períodos
            if self.periodo_ema_rapida >= self.periodo_ema_lenta:
                return False
            
            if self.periodo_ema_rapida < 5 or self.periodo_ema_lenta > 50:
                return False
            
            if self.periodo_rsi < 10 or self.periodo_rsi > 30:
                return False
            
            if self.periodo_atr < 10 or self.periodo_atr > 30:
                return False
            
            # Validar multiplicadores
            if self.multiplicador_stop <= 0 or self.multiplicador_stop > 5:
                return False
            
            if self.multiplicador_take_profit <= 1 or self.multiplicador_take_profit > 10:
                return False
            
            # Validar níveis de RSI
            if not (0 < self.rsi_sobrevenda < 50):
                return False
            
            if not (50 < self.rsi_sobrecompra < 100):
                return False
            
            # Validar outros parâmetros
            if self.min_volume_relativo < 1.0:
                return False
            
            if not (0 < self.min_forca_tendencia < 1):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação de parâmetros específicos: {e}")
            return False
    
    def obter_estado_estrategia(self) -> Dict[str, Any]:
        """
        Obtém estado atual da estratégia
        
        Returns:
            Dicionário com estado da estratégia
        """
        estado = self.obter_metricas_performance()
        estado.update({
            'tendencias_atuais': self.ultima_tendencia.copy(),
            'sinais_por_simbolo': {
                simbolo: len(sinais) 
                for simbolo, sinais in self.historico_sinais_por_simbolo.items()
            },
            'parametros_tecnicos': {
                'ema_rapida': self.periodo_ema_rapida,
                'ema_lenta': self.periodo_ema_lenta,
                'rsi': self.periodo_rsi,
                'atr': self.periodo_atr,
                'stop_multiplier': self.multiplicador_stop,
                'tp_multiplier': self.multiplicador_take_profit
            }
        })
        
        return estado
