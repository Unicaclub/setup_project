"""
Estratégia de Trading de Rompimento (Breakout)
Implementação de estratégia baseada em rompimentos de níveis de suporte e resistência
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal

from ..base_strategy import EstrategiaBase, SinalTrade, TipoSinal, DadosMercado


class EstrategiaBreakout(EstrategiaBase):
    """
    Estratégia de trading de rompimento (breakout)
    
    Características:
    - Identificação de níveis de suporte e resistência
    - Detecção de rompimentos com confirmação de volume
    - Stop loss abaixo/acima do nível rompido
    - Take profit baseado em projeção de movimento
    """
    
    def __init__(self, parametros: Dict[str, Any] = None):
        """
        Inicializa a estratégia de breakout
        
        Args:
            parametros: Parâmetros de configuração
        """
        parametros_padrao = {
            'periodo_lookback': 20,  # Períodos para identificar níveis
            'min_toques_nivel': 2,   # Mínimo de toques para confirmar nível
            'percentual_rompimento': 0.005,  # 0.5% para confirmar rompimento
            'multiplicador_volume': 1.5,     # Volume deve ser 1.5x a média
            'periodo_volume': 20,            # Períodos para média de volume
            'multiplicador_stop': 1.0,       # Stop loss como % do rompimento
            'razao_risco_retorno': 2.5,      # Razão risco/retorno mínima
            'max_idade_nivel': 100,          # Máxima idade do nível em períodos
            'min_forca_nivel': 0.6,          # Força mínima do nível (0-1)
            'filtro_tendencia': True         # Usar filtro de tendência
        }
        
        if parametros:
            parametros_padrao.update(parametros)
        
        super().__init__("Breakout Trader", parametros_padrao)
        
        # Parâmetros específicos
        self.periodo_lookback = self.parametros['periodo_lookback']
        self.min_toques_nivel = self.parametros['min_toques_nivel']
        self.percentual_rompimento = self.parametros['percentual_rompimento']
        self.multiplicador_volume = self.parametros['multiplicador_volume']
        self.periodo_volume = self.parametros['periodo_volume']
        self.multiplicador_stop = self.parametros['multiplicador_stop']
        self.razao_risco_retorno = self.parametros['razao_risco_retorno']
        self.max_idade_nivel = self.parametros['max_idade_nivel']
        self.min_forca_nivel = self.parametros['min_forca_nivel']
        self.filtro_tendencia = self.parametros['filtro_tendencia']
        
        # Estado interno
        self.niveis_suporte: Dict[str, List[Dict[str, Any]]] = {}
        self.niveis_resistencia: Dict[str, List[Dict[str, Any]]] = {}
        self.historico_rompimentos: Dict[str, List[Dict[str, Any]]] = {}
    
    async def _inicializar_especifica(self):
        """Inicialização específica da estratégia"""
        self.logger.info("Inicializando estratégia de breakout")
        self.logger.info(f"Parâmetros: Lookback({self.periodo_lookback}), "
                        f"Min toques({self.min_toques_nivel}), "
                        f"Rompimento({self.percentual_rompimento*100:.1f}%)")
    
    async def _finalizar_especifica(self):
        """Finalização específica da estratégia"""
        self.logger.info("Finalizando estratégia de breakout")
        self.niveis_suporte.clear()
        self.niveis_resistencia.clear()
        self.historico_rompimentos.clear()
    
    async def _analisar_especifica(self, dados_mercado: DadosMercado) -> Optional[SinalTrade]:
        """
        Análise específica da estratégia de breakout
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Sinal de trading se gerado, None caso contrário
        """
        try:
            simbolo = dados_mercado.simbolo
            precos = dados_mercado.precos
            
            # Verificar se temos dados suficientes
            min_periodos = max(self.periodo_lookback, self.periodo_volume) + 20
            if len(precos) < min_periodos:
                self.logger.debug(f"Dados insuficientes para {simbolo}: {len(precos)} < {min_periodos}")
                return None
            
            # Identificar níveis de suporte e resistência
            self._identificar_niveis(simbolo, precos)
            
            # Verificar rompimentos
            rompimento = self._verificar_rompimento(simbolo, precos, dados_mercado.volume)
            
            if rompimento:
                # Criar sinal baseado no rompimento
                sinal = self._criar_sinal_rompimento(simbolo, precos, dados_mercado.volume, rompimento)
                return sinal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro na análise específica para {dados_mercado.simbolo}: {e}")
            return None
    
    def _identificar_niveis(self, simbolo: str, precos: pd.DataFrame):
        """
        Identifica níveis de suporte e resistência
        
        Args:
            simbolo: Símbolo sendo analisado
            precos: DataFrame com dados de preços
        """
        # Inicializar listas se não existirem
        if simbolo not in self.niveis_suporte:
            self.niveis_suporte[simbolo] = []
        if simbolo not in self.niveis_resistencia:
            self.niveis_resistencia[simbolo] = []
        
        # Identificar máximos e mínimos locais
        maximos_locais = self._encontrar_maximos_locais(precos['high'])
        minimos_locais = self._encontrar_minimos_locais(precos['low'])
        
        # Processar níveis de resistência (máximos)
        for idx, preco in maximos_locais:
            self._processar_nivel_resistencia(simbolo, idx, preco, precos)
        
        # Processar níveis de suporte (mínimos)
        for idx, preco in minimos_locais:
            self._processar_nivel_suporte(simbolo, idx, preco, precos)
        
        # Limpar níveis antigos
        self._limpar_niveis_antigos(simbolo, len(precos))
    
    def _encontrar_maximos_locais(self, serie_precos: pd.Series) -> List[Tuple[int, float]]:
        """
        Encontra máximos locais na série de preços
        
        Args:
            serie_precos: Série de preços
            
        Returns:
            Lista de tuplas (índice, preço) dos máximos locais
        """
        maximos = []
        janela = self.periodo_lookback // 2
        
        for i in range(janela, len(serie_precos) - janela):
            preco_atual = serie_precos.iloc[i]
            
            # Verificar se é máximo local
            is_maximo = True
            for j in range(i - janela, i + janela + 1):
                if j != i and serie_precos.iloc[j] >= preco_atual:
                    is_maximo = False
                    break
            
            if is_maximo:
                maximos.append((i, preco_atual))
        
        return maximos
    
    def _encontrar_minimos_locais(self, serie_precos: pd.Series) -> List[Tuple[int, float]]:
        """
        Encontra mínimos locais na série de preços
        
        Args:
            serie_precos: Série de preços
            
        Returns:
            Lista de tuplas (índice, preço) dos mínimos locais
        """
        minimos = []
        janela = self.periodo_lookback // 2
        
        for i in range(janela, len(serie_precos) - janela):
            preco_atual = serie_precos.iloc[i]
            
            # Verificar se é mínimo local
            is_minimo = True
            for j in range(i - janela, i + janela + 1):
                if j != i and serie_precos.iloc[j] <= preco_atual:
                    is_minimo = False
                    break
            
            if is_minimo:
                minimos.append((i, preco_atual))
        
        return minimos
    
    def _processar_nivel_resistencia(self, simbolo: str, idx: int, preco: float, precos: pd.DataFrame):
        """
        Processa um nível de resistência identificado
        
        Args:
            simbolo: Símbolo
            idx: Índice do nível
            preco: Preço do nível
            precos: DataFrame de preços
        """
        tolerancia = preco * 0.002  # 0.2% de tolerância
        
        # Verificar se já existe nível próximo
        nivel_existente = None
        for nivel in self.niveis_resistencia[simbolo]:
            if abs(nivel['preco'] - preco) <= tolerancia:
                nivel_existente = nivel
                break
        
        if nivel_existente:
            # Atualizar nível existente
            nivel_existente['toques'] += 1
            nivel_existente['ultimo_toque'] = idx
            nivel_existente['forca'] = self._calcular_forca_nivel(nivel_existente)
        else:
            # Criar novo nível
            novo_nivel = {
                'preco': preco,
                'primeiro_toque': idx,
                'ultimo_toque': idx,
                'toques': 1,
                'tipo': 'resistencia',
                'forca': 0.5,  # Força inicial
                'idade': 0
            }
            self.niveis_resistencia[simbolo].append(novo_nivel)
    
    def _processar_nivel_suporte(self, simbolo: str, idx: int, preco: float, precos: pd.DataFrame):
        """
        Processa um nível de suporte identificado
        
        Args:
            simbolo: Símbolo
            idx: Índice do nível
            preco: Preço do nível
            precos: DataFrame de preços
        """
        tolerancia = preco * 0.002  # 0.2% de tolerância
        
        # Verificar se já existe nível próximo
        nivel_existente = None
        for nivel in self.niveis_suporte[simbolo]:
            if abs(nivel['preco'] - preco) <= tolerancia:
                nivel_existente = nivel
                break
        
        if nivel_existente:
            # Atualizar nível existente
            nivel_existente['toques'] += 1
            nivel_existente['ultimo_toque'] = idx
            nivel_existente['forca'] = self._calcular_forca_nivel(nivel_existente)
        else:
            # Criar novo nível
            novo_nivel = {
                'preco': preco,
                'primeiro_toque': idx,
                'ultimo_toque': idx,
                'toques': 1,
                'tipo': 'suporte',
                'forca': 0.5,  # Força inicial
                'idade': 0
            }
            self.niveis_suporte[simbolo].append(novo_nivel)
    
    def _calcular_forca_nivel(self, nivel: Dict[str, Any]) -> float:
        """
        Calcula a força de um nível baseado em múltiplos fatores
        
        Args:
            nivel: Dados do nível
            
        Returns:
            Força do nível (0-1)
        """
        # Fator baseado no número de toques
        fator_toques = min(nivel['toques'] / 5.0, 1.0)
        
        # Fator baseado na idade (níveis mais antigos são mais fortes)
        idade = nivel['ultimo_toque'] - nivel['primeiro_toque']
        fator_idade = min(idade / 50.0, 1.0)
        
        # Fator baseado na recência do último toque
        fator_recencia = max(0.3, 1.0 - (nivel['idade'] / 100.0))
        
        # Combinar fatores
        forca = (fator_toques * 0.4) + (fator_idade * 0.3) + (fator_recencia * 0.3)
        return min(forca, 1.0)
    
    def _limpar_niveis_antigos(self, simbolo: str, indice_atual: int):
        """
        Remove níveis muito antigos ou fracos
        
        Args:
            simbolo: Símbolo
            indice_atual: Índice atual dos dados
        """
        # Atualizar idade e filtrar níveis de resistência
        niveis_validos = []
        for nivel in self.niveis_resistencia[simbolo]:
            nivel['idade'] = indice_atual - nivel['ultimo_toque']
            
            if (nivel['idade'] <= self.max_idade_nivel and 
                nivel['toques'] >= self.min_toques_nivel and
                nivel['forca'] >= self.min_forca_nivel):
                niveis_validos.append(nivel)
        
        self.niveis_resistencia[simbolo] = niveis_validos
        
        # Atualizar idade e filtrar níveis de suporte
        niveis_validos = []
        for nivel in self.niveis_suporte[simbolo]:
            nivel['idade'] = indice_atual - nivel['ultimo_toque']
            
            if (nivel['idade'] <= self.max_idade_nivel and 
                nivel['toques'] >= self.min_toques_nivel and
                nivel['forca'] >= self.min_forca_nivel):
                niveis_validos.append(nivel)
        
        self.niveis_suporte[simbolo] = niveis_validos
    
    def _verificar_rompimento(self, simbolo: str, precos: pd.DataFrame, 
                            volume: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Verifica se houve rompimento de algum nível
        
        Args:
            simbolo: Símbolo
            precos: DataFrame de preços
            volume: Série de volume
            
        Returns:
            Dados do rompimento ou None
        """
        preco_atual = precos['close'].iloc[-1]
        volume_atual = volume.iloc[-1]
        volume_medio = volume.rolling(window=self.periodo_volume).mean().iloc[-1]
        
        # Verificar se volume confirma o rompimento
        if pd.isna(volume_medio) or volume_atual < volume_medio * self.multiplicador_volume:
            return None
        
        # Verificar rompimento de resistência (sinal de compra)
        for nivel in self.niveis_resistencia.get(simbolo, []):
            limite_rompimento = nivel['preco'] * (1 + self.percentual_rompimento)
            
            if preco_atual > limite_rompimento:
                return {
                    'tipo': TipoSinal.COMPRA,
                    'nivel_rompido': nivel,
                    'preco_rompimento': preco_atual,
                    'volume_confirmacao': volume_atual / volume_medio,
                    'direcao': 'alta'
                }
        
        # Verificar rompimento de suporte (sinal de venda)
        for nivel in self.niveis_suporte.get(simbolo, []):
            limite_rompimento = nivel['preco'] * (1 - self.percentual_rompimento)
            
            if preco_atual < limite_rompimento:
                return {
                    'tipo': TipoSinal.VENDA,
                    'nivel_rompido': nivel,
                    'preco_rompimento': preco_atual,
                    'volume_confirmacao': volume_atual / volume_medio,
                    'direcao': 'baixa'
                }
        
        return None
    
    def _criar_sinal_rompimento(self, simbolo: str, precos: pd.DataFrame, 
                              volume: pd.Series, rompimento: Dict[str, Any]) -> SinalTrade:
        """
        Cria sinal baseado no rompimento detectado
        
        Args:
            simbolo: Símbolo
            precos: DataFrame de preços
            volume: Série de volume
            rompimento: Dados do rompimento
            
        Returns:
            Sinal de trading
        """
        preco_atual = Decimal(str(rompimento['preco_rompimento']))
        nivel_rompido = rompimento['nivel_rompido']
        preco_nivel = Decimal(str(nivel_rompido['preco']))
        
        # Calcular stop loss
        if rompimento['tipo'] == TipoSinal.COMPRA:
            # Stop loss abaixo do nível rompido
            distancia_stop = abs(preco_atual - preco_nivel) * Decimal(str(self.multiplicador_stop))
            stop_loss = preco_nivel - distancia_stop
        else:
            # Stop loss acima do nível rompido
            distancia_stop = abs(preco_nivel - preco_atual) * Decimal(str(self.multiplicador_stop))
            stop_loss = preco_nivel + distancia_stop
        
        # Calcular take profit baseado na razão risco/retorno
        risco = abs(preco_atual - stop_loss)
        retorno_esperado = risco * Decimal(str(self.razao_risco_retorno))
        
        if rompimento['tipo'] == TipoSinal.COMPRA:
            take_profit = preco_atual + retorno_esperado
        else:
            take_profit = preco_atual - retorno_esperado
        
        # Calcular confiança do sinal
        confianca = self._calcular_confianca_rompimento(rompimento)
        
        # Calcular força do sinal
        forca = min(nivel_rompido['forca'] * rompimento['volume_confirmacao'] / 2.0, 1.0)
        
        sinal = SinalTrade(
            simbolo=simbolo,
            tipo=rompimento['tipo'],
            forca=forca,
            preco_entrada=preco_atual,
            stop_loss=stop_loss,
            take_profit=take_profit,
            razao_risco_retorno=self.razao_risco_retorno,
            confianca=confianca,
            metadados={
                'estrategia': self.nome,
                'tipo_rompimento': rompimento['direcao'],
                'nivel_rompido': nivel_rompido['preco'],
                'forca_nivel': nivel_rompido['forca'],
                'toques_nivel': nivel_rompido['toques'],
                'idade_nivel': nivel_rompido['idade'],
                'volume_confirmacao': rompimento['volume_confirmacao'],
                'percentual_rompimento': self.percentual_rompimento
            }
        )
        
        # Registrar no histórico
        if simbolo not in self.historico_rompimentos:
            self.historico_rompimentos[simbolo] = []
        
        self.historico_rompimentos[simbolo].append({
            'timestamp': sinal.timestamp,
            'tipo': sinal.tipo.value,
            'preco': float(preco_atual),
            'nivel_rompido': nivel_rompido['preco'],
            'forca_nivel': nivel_rompido['forca'],
            'volume_confirmacao': rompimento['volume_confirmacao']
        })
        
        # Limitar histórico
        if len(self.historico_rompimentos[simbolo]) > 50:
            self.historico_rompimentos[simbolo].pop(0)
        
        return sinal
    
    def _calcular_confianca_rompimento(self, rompimento: Dict[str, Any]) -> float:
        """
        Calcula confiança do rompimento baseada em múltiplos fatores
        
        Args:
            rompimento: Dados do rompimento
            
        Returns:
            Confiança do sinal (0-1)
        """
        fatores_confianca = []
        
        # Força do nível rompido
        fatores_confianca.append(rompimento['nivel_rompido']['forca'])
        
        # Confirmação de volume
        volume_factor = min(rompimento['volume_confirmacao'] / 2.0, 1.0)
        fatores_confianca.append(volume_factor)
        
        # Número de toques no nível
        toques = rompimento['nivel_rompido']['toques']
        fator_toques = min(toques / 5.0, 1.0)
        fatores_confianca.append(fator_toques)
        
        # Idade do nível (níveis mais estabelecidos são mais confiáveis)
        idade = rompimento['nivel_rompido']['idade']
        if idade < 10:
            fator_idade = 0.5
        elif idade < 30:
            fator_idade = 0.8
        else:
            fator_idade = 1.0
        
        fatores_confianca.append(fator_idade)
        
        # Calcular média ponderada
        pesos = [0.3, 0.3, 0.2, 0.2]
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
            if self.periodo_lookback < 10 or self.periodo_lookback > 100:
                return False
            
            if self.periodo_volume < 10 or self.periodo_volume > 50:
                return False
            
            # Validar contadores
            if self.min_toques_nivel < 2 or self.min_toques_nivel > 10:
                return False
            
            # Validar percentuais
            if not (0.001 <= self.percentual_rompimento <= 0.02):  # 0.1% a 2%
                return False
            
            if self.multiplicador_volume < 1.0 or self.multiplicador_volume > 5.0:
                return False
            
            if self.multiplicador_stop < 0.5 or self.multiplicador_stop > 3.0:
                return False
            
            if self.razao_risco_retorno < 1.0 or self.razao_risco_retorno > 10.0:
                return False
            
            # Validar limites
            if self.max_idade_nivel < 20 or self.max_idade_nivel > 500:
                return False
            
            if not (0.1 <= self.min_forca_nivel <= 1.0):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação de parâmetros específicos: {e}")
            return False
    
    def obter_niveis_atuais(self, simbolo: str) -> Dict[str, Any]:
        """
        Obtém níveis atuais de suporte e resistência
        
        Args:
            simbolo: Símbolo para consultar
            
        Returns:
            Dicionário com níveis atuais
        """
        return {
            'suporte': [
                {
                    'preco': nivel['preco'],
                    'forca': nivel['forca'],
                    'toques': nivel['toques'],
                    'idade': nivel['idade']
                }
                for nivel in self.niveis_suporte.get(simbolo, [])
            ],
            'resistencia': [
                {
                    'preco': nivel['preco'],
                    'forca': nivel['forca'],
                    'toques': nivel['toques'],
                    'idade': nivel['idade']
                }
                for nivel in self.niveis_resistencia.get(simbolo, [])
            ]
        }
    
    def obter_estatisticas_rompimentos(self, simbolo: str = None) -> Dict[str, Any]:
        """
        Obtém estatísticas de rompimentos
        
        Args:
            simbolo: Símbolo específico ou None para todos
            
        Returns:
            Estatísticas de rompimentos
        """
        if simbolo:
            historico = self.historico_rompimentos.get(simbolo, [])
            simbolos = [simbolo]
        else:
            historico = []
            for hist in self.historico_rompimentos.values():
                historico.extend(hist)
            simbolos = list(self.historico_rompimentos.keys())
        
        if not historico:
            return {
                'total_rompimentos': 0,
                'simbolos_analisados': len(simbolos),
                'rompimentos_alta': 0,
                'rompimentos_baixa': 0,
                'forca_media_niveis': 0,
                'volume_confirmacao_medio': 0
            }
        
        # Separar por tipo
        rompimentos_alta = [h for h in historico if h['tipo'] == 'compra']
        rompimentos_baixa = [h for h in historico if h['tipo'] == 'venda']
        
        return {
            'total_rompimentos': len(historico),
            'simbolos_analisados': len(simbolos),
            'rompimentos_alta': len(rompimentos_alta),
            'rompimentos_baixa': len(rompimentos_baixa),
            'forca_media_niveis': sum(h['forca_nivel'] for h in historico) / len(historico),
            'volume_confirmacao_medio': sum(h['volume_confirmacao'] for h in historico) / len(historico)
        }
    
    def obter_estado_estrategia(self) -> Dict[str, Any]:
        """
        Obtém estado atual da estratégia
        
        Returns:
            Dicionário com estado da estratégia
        """
        estado = self.obter_metricas_performance()
        
        # Contar níveis por símbolo
        total_suporte = sum(len(niveis) for niveis in self.niveis_suporte.values())
        total_resistencia = sum(len(niveis) for niveis in self.niveis_resistencia.values())
        
        estado.update({
            'niveis_suporte_ativos': total_suporte,
            'niveis_resistencia_ativos': total_resistencia,
            'simbolos_monitorados': len(set(list(self.niveis_suporte.keys()) + 
                                          list(self.niveis_resistencia.keys()))),
            'estatisticas_rompimentos': self.obter_estatisticas_rompimentos(),
            'parametros_tecnicos': {
                'periodo_lookback': self.periodo_lookback,
                'min_toques_nivel': self.min_toques_nivel,
                'percentual_rompimento': self.percentual_rompimento,
                'multiplicador_volume': self.multiplicador_volume,
                'razao_risco_retorno': self.razao_risco_retorno,
                'max_idade_nivel': self.max_idade_nivel,
                'min_forca_nivel': self.min_forca_nivel
            }
        })
        
        return estado
