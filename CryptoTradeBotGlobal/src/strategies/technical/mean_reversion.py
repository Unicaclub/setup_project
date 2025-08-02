"""
Estratégia de Reversão à Média
Implementação de estratégia baseada em Bandas de Bollinger e RSI
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal

from ..base_strategy import EstrategiaBase, SinalTrade, TipoSinal, DadosMercado


class EstrategiaReversaoMedia(EstrategiaBase):
    """
    Estratégia de reversão à média usando Bandas de Bollinger e RSI
    
    Características:
    - Identificação de condições de sobrecompra/sobrevenda
    - Entrada quando preço toca bandas de Bollinger
    - Confirmação com RSI em níveis extremos
    - Stop loss conservador e take profit na média móvel
    """
    
    def __init__(self, parametros: Dict[str, Any] = None):
        """
        Inicializa a estratégia de reversão à média
        
        Args:
            parametros: Parâmetros de configuração
        """
        parametros_padrao = {
            'periodo_bollinger': 20,
            'desvios_bollinger': 2.0,
            'periodo_rsi': 14,
            'rsi_sobrecompra': 75,
            'rsi_sobrevenda': 25,
            'periodo_atr': 14,
            'multiplicador_stop': 1.5,
            'percentual_take_profit': 0.8,  # 80% do caminho até a média
            'min_distancia_banda': 0.02,  # 2% mínimo de distância da banda
            'max_volatilidade': 0.05,  # 5% máximo de volatilidade
            'min_volume_relativo': 1.1
        }
        
        if parametros:
            parametros_padrao.update(parametros)
        
        super().__init__("Reversão à Média", parametros_padrao)
        
        # Parâmetros específicos
        self.periodo_bollinger = self.parametros['periodo_bollinger']
        self.desvios_bollinger = self.parametros['desvios_bollinger']
        self.periodo_rsi = self.parametros['periodo_rsi']
        self.rsi_sobrecompra = self.parametros['rsi_sobrecompra']
        self.rsi_sobrevenda = self.parametros['rsi_sobrevenda']
        self.periodo_atr = self.parametros['periodo_atr']
        self.multiplicador_stop = self.parametros['multiplicador_stop']
        self.percentual_take_profit = self.parametros['percentual_take_profit']
        self.min_distancia_banda = self.parametros['min_distancia_banda']
        self.max_volatilidade = self.parametros['max_volatilidade']
        self.min_volume_relativo = self.parametros['min_volume_relativo']
        
        # Estado interno
        self.posicoes_ativas: Dict[str, Dict[str, Any]] = {}
        self.historico_reversoes: Dict[str, List[Dict[str, Any]]] = {}
    
    async def _inicializar_especifica(self):
        """Inicialização específica da estratégia"""
        self.logger.info("Inicializando estratégia de reversão à média")
        self.logger.info(f"Parâmetros: Bollinger({self.periodo_bollinger}, {self.desvios_bollinger}), "
                        f"RSI({self.periodo_rsi}), ATR({self.periodo_atr})")
    
    async def _finalizar_especifica(self):
        """Finalização específica da estratégia"""
        self.logger.info("Finalizando estratégia de reversão à média")
        self.posicoes_ativas.clear()
        self.historico_reversoes.clear()
    
    async def _analisar_especifica(self, dados_mercado: DadosMercado) -> Optional[SinalTrade]:
        """
        Análise específica da estratégia de reversão à média
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Sinal de trading se gerado, None caso contrário
        """
        try:
            simbolo = dados_mercado.simbolo
            precos = dados_mercado.precos
            
            # Verificar se temos dados suficientes
            min_periodos = max(self.periodo_bollinger, self.periodo_rsi, self.periodo_atr) + 10
            if len(precos) < min_periodos:
                self.logger.debug(f"Dados insuficientes para {simbolo}: {len(precos)} < {min_periodos}")
                return None
            
            # Calcular indicadores
            indicadores = self._calcular_indicadores(precos, dados_mercado.volume)
            
            # Verificar condições de mercado
            if not self._verificar_condicoes_mercado(indicadores):
                return None
            
            # Analisar oportunidades de reversão
            oportunidade = self._analisar_oportunidade_reversao(indicadores, simbolo)
            
            if oportunidade:
                # Criar sinal baseado na oportunidade
                sinal = self._criar_sinal_reversao(
                    simbolo, precos, indicadores, oportunidade
                )
                return sinal
            
            return None
            
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
        
        # Bandas de Bollinger
        banda_superior, media_movel, banda_inferior = self.calcular_bandas_bollinger(
            precos['close'], self.periodo_bollinger, self.desvios_bollinger
        )
        indicadores['banda_superior'] = banda_superior
        indicadores['media_movel'] = media_movel
        indicadores['banda_inferior'] = banda_inferior
        
        # RSI
        indicadores['rsi'] = self.calcular_rsi(precos['close'], self.periodo_rsi)
        
        # ATR para stop loss
        indicadores['atr'] = self._calcular_atr(precos, self.periodo_atr)
        
        # Volatilidade
        indicadores['volatilidade'] = precos['close'].pct_change().rolling(window=20).std()
        
        # Volume relativo
        indicadores['volume_ma'] = volume.rolling(window=20).mean()
        indicadores['volume_relativo'] = volume / indicadores['volume_ma']
        
        # Posição do preço nas bandas (0 = banda inferior, 1 = banda superior)
        largura_banda = banda_superior - banda_inferior
        indicadores['posicao_banda'] = (precos['close'] - banda_inferior) / largura_banda
        
        # Distância percentual das bandas
        indicadores['distancia_banda_sup'] = (banda_superior - precos['close']) / precos['close']
        indicadores['distancia_banda_inf'] = (precos['close'] - banda_inferior) / precos['close']
        
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
    
    def _verificar_condicoes_mercado(self, indicadores: Dict[str, pd.Series]) -> bool:
        """
        Verifica se as condições de mercado são adequadas para reversão à média
        
        Args:
            indicadores: Indicadores calculados
            
        Returns:
            True se condições são adequadas
        """
        # Verificar volatilidade
        volatilidade_atual = indicadores['volatilidade'].iloc[-1]
        if pd.isna(volatilidade_atual) or volatilidade_atual > self.max_volatilidade:
            return False
        
        # Verificar volume
        volume_relativo = indicadores['volume_relativo'].iloc[-1]
        if pd.isna(volume_relativo) or volume_relativo < self.min_volume_relativo:
            return False
        
        # Verificar se as bandas não estão muito próximas (mercado sem volatilidade)
        distancia_banda_sup = indicadores['distancia_banda_sup'].iloc[-1]
        distancia_banda_inf = indicadores['distancia_banda_inf'].iloc[-1]
        
        if (pd.isna(distancia_banda_sup) or pd.isna(distancia_banda_inf) or
            max(distancia_banda_sup, distancia_banda_inf) < self.min_distancia_banda):
            return False
        
        return True
    
    def _analisar_oportunidade_reversao(self, indicadores: Dict[str, pd.Series], 
                                      simbolo: str) -> Optional[Dict[str, Any]]:
        """
        Analisa oportunidades de reversão à média
        
        Args:
            indicadores: Indicadores calculados
            simbolo: Símbolo sendo analisado
            
        Returns:
            Dicionário com dados da oportunidade ou None
        """
        rsi_atual = indicadores['rsi'].iloc[-1]
        posicao_banda = indicadores['posicao_banda'].iloc[-1]
        
        # Verificar se RSI e posição nas bandas indicam extremos
        if pd.isna(rsi_atual) or pd.isna(posicao_banda):
            return None
        
        # Oportunidade de compra (preço na banda inferior + RSI sobrevenda)
        if (posicao_banda <= 0.1 and  # Próximo à banda inferior
            rsi_atual <= self.rsi_sobrevenda):
            
            return {
                'tipo': TipoSinal.COMPRA,
                'forca': self._calcular_forca_reversao(rsi_atual, posicao_banda, 'compra'),
                'rsi': rsi_atual,
                'posicao_banda': posicao_banda,
                'razao': 'sobrevenda'
            }
        
        # Oportunidade de venda (preço na banda superior + RSI sobrecompra)
        elif (posicao_banda >= 0.9 and  # Próximo à banda superior
              rsi_atual >= self.rsi_sobrecompra):
            
            return {
                'tipo': TipoSinal.VENDA,
                'forca': self._calcular_forca_reversao(rsi_atual, posicao_banda, 'venda'),
                'rsi': rsi_atual,
                'posicao_banda': posicao_banda,
                'razao': 'sobrecompra'
            }
        
        return None
    
    def _calcular_forca_reversao(self, rsi: float, posicao_banda: float, tipo: str) -> float:
        """
        Calcula a força do sinal de reversão
        
        Args:
            rsi: Valor atual do RSI
            posicao_banda: Posição nas bandas de Bollinger
            tipo: Tipo do sinal ('compra' ou 'venda')
            
        Returns:
            Força do sinal (0-1)
        """
        if tipo == 'compra':
            # Quanto menor o RSI e mais próximo da banda inferior, maior a força
            forca_rsi = max(0, (self.rsi_sobrevenda - rsi) / self.rsi_sobrevenda)
            forca_banda = max(0, (0.1 - posicao_banda) / 0.1)
        else:  # venda
            # Quanto maior o RSI e mais próximo da banda superior, maior a força
            forca_rsi = max(0, (rsi - self.rsi_sobrecompra) / (100 - self.rsi_sobrecompra))
            forca_banda = max(0, (posicao_banda - 0.9) / 0.1)
        
        # Média ponderada das forças
        forca_total = (forca_rsi * 0.6) + (forca_banda * 0.4)
        return min(forca_total, 1.0)
    
    def _criar_sinal_reversao(self, simbolo: str, precos: pd.DataFrame, 
                            indicadores: Dict[str, pd.Series], 
                            oportunidade: Dict[str, Any]) -> SinalTrade:
        """
        Cria sinal de reversão à média
        
        Args:
            simbolo: Símbolo
            precos: DataFrame com preços
            indicadores: Indicadores calculados
            oportunidade: Dados da oportunidade
            
        Returns:
            Sinal de trading
        """
        preco_atual = Decimal(str(precos['close'].iloc[-1]))
        media_movel = Decimal(str(indicadores['media_movel'].iloc[-1]))
        atr = indicadores['atr'].iloc[-1]
        
        if oportunidade['tipo'] == TipoSinal.COMPRA:
            # Sinal de compra (reversão de baixa para alta)
            stop_loss = preco_atual - Decimal(str(atr * self.multiplicador_stop))
            
            # Take profit em direção à média móvel
            distancia_media = media_movel - preco_atual
            take_profit = preco_atual + (distancia_media * Decimal(str(self.percentual_take_profit)))
            
        else:  # VENDA
            # Sinal de venda (reversão de alta para baixa)
            stop_loss = preco_atual + Decimal(str(atr * self.multiplicador_stop))
            
            # Take profit em direção à média móvel
            distancia_media = preco_atual - media_movel
            take_profit = preco_atual - (distancia_media * Decimal(str(self.percentual_take_profit)))
        
        # Calcular razão risco/retorno
        risco = abs(preco_atual - stop_loss)
        retorno = abs(take_profit - preco_atual)
        razao_rr = float(retorno / risco) if risco > 0 else 1.0
        
        # Calcular confiança
        confianca = self._calcular_confianca_sinal(oportunidade, indicadores)
        
        sinal = SinalTrade(
            simbolo=simbolo,
            tipo=oportunidade['tipo'],
            forca=oportunidade['forca'],
            preco_entrada=preco_atual,
            stop_loss=stop_loss,
            take_profit=take_profit,
            razao_risco_retorno=razao_rr,
            confianca=confianca,
            metadados={
                'estrategia': self.nome,
                'razao_reversao': oportunidade['razao'],
                'rsi': oportunidade['rsi'],
                'posicao_banda': oportunidade['posicao_banda'],
                'media_movel': float(media_movel),
                'atr': atr,
                'volatilidade': indicadores['volatilidade'].iloc[-1],
                'volume_relativo': indicadores['volume_relativo'].iloc[-1]
            }
        )
        
        # Registrar no histórico
        if simbolo not in self.historico_reversoes:
            self.historico_reversoes[simbolo] = []
        
        self.historico_reversoes[simbolo].append({
            'timestamp': sinal.timestamp,
            'tipo': sinal.tipo.value,
            'preco': float(preco_atual),
            'rsi': oportunidade['rsi'],
            'posicao_banda': oportunidade['posicao_banda']
        })
        
        # Limitar histórico
        if len(self.historico_reversoes[simbolo]) > 100:
            self.historico_reversoes[simbolo].pop(0)
        
        return sinal
    
    def _calcular_confianca_sinal(self, oportunidade: Dict[str, Any], 
                                 indicadores: Dict[str, pd.Series]) -> float:
        """
        Calcula confiança do sinal baseada em múltiplos fatores
        
        Args:
            oportunidade: Dados da oportunidade
            indicadores: Indicadores calculados
            
        Returns:
            Confiança do sinal (0-1)
        """
        fatores_confianca = []
        
        # Força da reversão
        fatores_confianca.append(oportunidade['forca'])
        
        # Extremo do RSI
        rsi = oportunidade['rsi']
        if oportunidade['tipo'] == TipoSinal.COMPRA:
            # Quanto menor o RSI, maior a confiança para compra
            fator_rsi = max(0, (30 - rsi) / 30) if rsi < 30 else 0.5
        else:
            # Quanto maior o RSI, maior a confiança para venda
            fator_rsi = max(0, (rsi - 70) / 30) if rsi > 70 else 0.5
        
        fatores_confianca.append(fator_rsi)
        
        # Posição nas bandas
        posicao_banda = oportunidade['posicao_banda']
        if oportunidade['tipo'] == TipoSinal.COMPRA:
            fator_banda = max(0, (0.2 - posicao_banda) / 0.2)
        else:
            fator_banda = max(0, (posicao_banda - 0.8) / 0.2)
        
        fatores_confianca.append(fator_banda)
        
        # Volume (maior volume = maior confiança)
        volume_relativo = indicadores['volume_relativo'].iloc[-1]
        fator_volume = min(volume_relativo / 2.0, 1.0)  # Normalizar
        fatores_confianca.append(fator_volume)
        
        # Volatilidade (volatilidade moderada é melhor)
        volatilidade = indicadores['volatilidade'].iloc[-1]
        if pd.notna(volatilidade):
            # Volatilidade ideal entre 1% e 3%
            if 0.01 <= volatilidade <= 0.03:
                fator_volatilidade = 0.9
            elif volatilidade < 0.01:
                fator_volatilidade = 0.6  # Muito baixa
            else:
                fator_volatilidade = max(0.3, 1.0 - (volatilidade - 0.03) / 0.02)
        else:
            fator_volatilidade = 0.5
        
        fatores_confianca.append(fator_volatilidade)
        
        # Calcular média ponderada
        pesos = [0.25, 0.25, 0.20, 0.15, 0.15]  # Pesos para cada fator
        confianca = sum(f * p for f, p in zip(fatores_confianca, pesos))
        
        return min(confianca, 1.0)
    
    def _validar_parametros_especificos(self) -> bool:
        """
        Validação específica de parâmetros da estratégia
        
        Returns:
            True se parâmetros específicos são válidos
        """
        try:
            # Validar períodos
            if self.periodo_bollinger < 10 or self.periodo_bollinger > 50:
                return False
            
            if self.periodo_rsi < 10 or self.periodo_rsi > 30:
                return False
            
            if self.periodo_atr < 10 or self.periodo_atr > 30:
                return False
            
            # Validar desvios de Bollinger
            if self.desvios_bollinger < 1.0 or self.desvios_bollinger > 3.0:
                return False
            
            # Validar níveis de RSI
            if not (10 <= self.rsi_sobrevenda <= 40):
                return False
            
            if not (60 <= self.rsi_sobrecompra <= 90):
                return False
            
            if self.rsi_sobrevenda >= self.rsi_sobrecompra:
                return False
            
            # Validar multiplicadores e percentuais
            if self.multiplicador_stop <= 0 or self.multiplicador_stop > 3:
                return False
            
            if not (0.5 <= self.percentual_take_profit <= 1.0):
                return False
            
            if not (0.01 <= self.min_distancia_banda <= 0.1):
                return False
            
            if not (0.01 <= self.max_volatilidade <= 0.2):
                return False
            
            if self.min_volume_relativo < 1.0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação de parâmetros específicos: {e}")
            return False
    
    def obter_estatisticas_reversao(self, simbolo: str = None) -> Dict[str, Any]:
        """
        Obtém estatísticas de reversão para um símbolo ou todos
        
        Args:
            simbolo: Símbolo específico ou None para todos
            
        Returns:
            Estatísticas de reversão
        """
        if simbolo:
            historico = self.historico_reversoes.get(simbolo, [])
            simbolos = [simbolo]
        else:
            historico = []
            for hist in self.historico_reversoes.values():
                historico.extend(hist)
            simbolos = list(self.historico_reversoes.keys())
        
        if not historico:
            return {
                'total_reversoes': 0,
                'simbolos_analisados': len(simbolos),
                'reversoes_compra': 0,
                'reversoes_venda': 0,
                'rsi_medio_compra': 0,
                'rsi_medio_venda': 0
            }
        
        # Separar por tipo
        compras = [h for h in historico if h['tipo'] == 'compra']
        vendas = [h for h in historico if h['tipo'] == 'venda']
        
        return {
            'total_reversoes': len(historico),
            'simbolos_analisados': len(simbolos),
            'reversoes_compra': len(compras),
            'reversoes_venda': len(vendas),
            'rsi_medio_compra': sum(c['rsi'] for c in compras) / len(compras) if compras else 0,
            'rsi_medio_venda': sum(v['rsi'] for v in vendas) / len(vendas) if vendas else 0,
            'posicao_banda_media_compra': sum(c['posicao_banda'] for c in compras) / len(compras) if compras else 0,
            'posicao_banda_media_venda': sum(v['posicao_banda'] for v in vendas) / len(vendas) if vendas else 0
        }
    
    def obter_estado_estrategia(self) -> Dict[str, Any]:
        """
        Obtém estado atual da estratégia
        
        Returns:
            Dicionário com estado da estratégia
        """
        estado = self.obter_metricas_performance()
        estado.update({
            'posicoes_ativas': len(self.posicoes_ativas),
            'estatisticas_reversao': self.obter_estatisticas_reversao(),
            'parametros_tecnicos': {
                'bollinger_periodo': self.periodo_bollinger,
                'bollinger_desvios': self.desvios_bollinger,
                'rsi_periodo': self.periodo_rsi,
                'rsi_sobrecompra': self.rsi_sobrecompra,
                'rsi_sobrevenda': self.rsi_sobrevenda,
                'atr_periodo': self.periodo_atr,
                'stop_multiplier': self.multiplicador_stop,
                'take_profit_pct': self.percentual_take_profit
            }
        })
        
        return estado
