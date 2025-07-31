"""
Estratégia Base para CryptoTradeBotGlobal
Classe abstrata base para todas as estratégias de trading
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from decimal import Decimal


class TipoSinal(Enum):
    """Tipos de sinal de trading"""
    COMPRA = "compra"
    VENDA = "venda"
    NEUTRO = "neutro"


class ForcaSinal(Enum):
    """Força do sinal de trading"""
    FRACO = 0.3
    MODERADO = 0.6
    FORTE = 0.8
    MUITO_FORTE = 1.0


@dataclass
class SinalTrade:
    """Estrutura de dados para sinal de trading"""
    simbolo: str
    tipo: TipoSinal
    forca: float
    preco_entrada: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    timestamp: float = field(default_factory=time.time)
    razao_risco_retorno: float = 2.0
    confianca: float = 0.5
    metadados: Dict[str, Any] = field(default_factory=dict)
    
    def para_dict(self) -> Dict[str, Any]:
        """Converte sinal para dicionário"""
        return {
            'simbolo': self.simbolo,
            'tipo': self.tipo.value,
            'forca': self.forca,
            'preco_entrada': float(self.preco_entrada),
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': float(self.take_profit) if self.take_profit else None,
            'timestamp': self.timestamp,
            'razao_risco_retorno': self.razao_risco_retorno,
            'confianca': self.confianca,
            'metadados': self.metadados
        }


@dataclass
class DadosMercado:
    """Dados de mercado para análise"""
    simbolo: str
    precos: pd.DataFrame  # OHLCV data
    volume: pd.Series
    timestamp: float = field(default_factory=time.time)
    indicadores: Dict[str, pd.Series] = field(default_factory=dict)
    
    def obter_preco_atual(self) -> Decimal:
        """Obtém o preço atual (último fechamento)"""
        if self.precos.empty:
            return Decimal('0')
        return Decimal(str(self.precos['close'].iloc[-1]))
    
    def obter_volatilidade(self, periodos: int = 20) -> float:
        """Calcula volatilidade dos preços"""
        if len(self.precos) < periodos:
            return 0.0
        
        retornos = self.precos['close'].pct_change().dropna()
        return float(retornos.tail(periodos).std())


class EstrategiaBase(ABC):
    """
    Classe base abstrata para todas as estratégias de trading
    
    Define a interface comum que todas as estratégias devem implementar
    para garantir consistência e intercambiabilidade.
    """
    
    def __init__(self, nome: str, parametros: Dict[str, Any] = None):
        """
        Inicializa a estratégia base
        
        Args:
            nome: Nome da estratégia
            parametros: Parâmetros de configuração da estratégia
        """
        self.nome = nome
        self.parametros = parametros or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Estado da estratégia
        self.ativa = False
        self.inicializada = False
        self.ultima_analise = 0.0
        
        # Métricas de performance
        self.sinais_gerados = 0
        self.sinais_corretos = 0
        self.sinais_incorretos = 0
        self.lucro_total = Decimal('0')
        self.perda_total = Decimal('0')
        
        # Configurações padrão
        self.intervalo_analise = self.parametros.get('intervalo_analise', 60)  # segundos
        self.min_confianca = self.parametros.get('min_confianca', 0.6)
        self.max_risco_por_trade = self.parametros.get('max_risco_por_trade', 0.02)
        
        # Cache de dados
        self.cache_dados: Dict[str, DadosMercado] = {}
        self.historico_sinais: List[SinalTrade] = []
    
    async def inicializar(self) -> bool:
        """
        Inicializa a estratégia
        
        Returns:
            True se inicializada com sucesso
        """
        try:
            self.logger.info(f"Inicializando estratégia {self.nome}")
            
            # Validar parâmetros
            if not self._validar_parametros():
                raise ValueError("Parâmetros inválidos")
            
            # Inicialização específica da estratégia
            await self._inicializar_especifica()
            
            self.inicializada = True
            self.logger.info(f"Estratégia {self.nome} inicializada com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar estratégia {self.nome}: {e}")
            return False
    
    async def finalizar(self):
        """Finaliza a estratégia e limpa recursos"""
        try:
            self.ativa = False
            await self._finalizar_especifica()
            self.logger.info(f"Estratégia {self.nome} finalizada")
            
        except Exception as e:
            self.logger.error(f"Erro ao finalizar estratégia {self.nome}: {e}")
    
    async def analisar(self, dados_mercado: DadosMercado) -> Optional[SinalTrade]:
        """
        Análise principal da estratégia
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Sinal de trading se gerado, None caso contrário
        """
        if not self.inicializada or not self.ativa:
            return None
        
        try:
            # Verificar se é hora de analisar
            agora = time.time()
            if agora - self.ultima_analise < self.intervalo_analise:
                return None
            
            self.ultima_analise = agora
            
            # Atualizar cache de dados
            self.cache_dados[dados_mercado.simbolo] = dados_mercado
            
            # Análise específica da estratégia
            sinal = await self._analisar_especifica(dados_mercado)
            
            if sinal and self._validar_sinal(sinal):
                self.sinais_gerados += 1
                self.historico_sinais.append(sinal)
                
                # Limitar histórico
                if len(self.historico_sinais) > 1000:
                    self.historico_sinais.pop(0)
                
                self.logger.info(f"Sinal gerado: {sinal.simbolo} {sinal.tipo.value} força={sinal.forca}")
                return sinal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro na análise da estratégia {self.nome}: {e}")
            return None
    
    def calcular_risco(self, sinal: SinalTrade, saldo_disponivel: Decimal) -> Dict[str, Any]:
        """
        Calcula métricas de risco para o sinal
        
        Args:
            sinal: Sinal de trading
            saldo_disponivel: Saldo disponível para trading
            
        Returns:
            Dicionário com métricas de risco
        """
        try:
            # Calcular tamanho da posição baseado no risco
            if sinal.stop_loss:
                risco_por_unidade = abs(sinal.preco_entrada - sinal.stop_loss)
                valor_risco = saldo_disponivel * Decimal(str(self.max_risco_por_trade))
                tamanho_posicao = valor_risco / risco_por_unidade
            else:
                # Sem stop loss, usar 2% do saldo como tamanho máximo
                tamanho_posicao = saldo_disponivel * Decimal('0.02') / sinal.preco_entrada
            
            # Calcular potencial de lucro
            potencial_lucro = Decimal('0')
            if sinal.take_profit:
                potencial_lucro = abs(sinal.take_profit - sinal.preco_entrada) * tamanho_posicao
            
            # Calcular potencial de perda
            potencial_perda = Decimal('0')
            if sinal.stop_loss:
                potencial_perda = abs(sinal.preco_entrada - sinal.stop_loss) * tamanho_posicao
            
            return {
                'tamanho_posicao': float(tamanho_posicao),
                'valor_posicao': float(tamanho_posicao * sinal.preco_entrada),
                'potencial_lucro': float(potencial_lucro),
                'potencial_perda': float(potencial_perda),
                'razao_risco_retorno': sinal.razao_risco_retorno,
                'percentual_risco': float(potencial_perda / saldo_disponivel * 100) if saldo_disponivel > 0 else 0,
                'confianca_sinal': sinal.confianca
            }
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo de risco: {e}")
            return {
                'tamanho_posicao': 0,
                'valor_posicao': 0,
                'potencial_lucro': 0,
                'potencial_perda': 0,
                'razao_risco_retorno': 0,
                'percentual_risco': 0,
                'confianca_sinal': 0
            }
    
    def atualizar_performance(self, resultado_trade: Dict[str, Any]):
        """
        Atualiza métricas de performance da estratégia
        
        Args:
            resultado_trade: Resultado do trade executado
        """
        try:
            lucro_perda = Decimal(str(resultado_trade.get('lucro_perda', 0)))
            
            if lucro_perda > 0:
                self.sinais_corretos += 1
                self.lucro_total += lucro_perda
            else:
                self.sinais_incorretos += 1
                self.perda_total += abs(lucro_perda)
            
            self.logger.debug(f"Performance atualizada: {self.obter_metricas_performance()}")
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar performance: {e}")
    
    def obter_metricas_performance(self) -> Dict[str, Any]:
        """
        Obtém métricas de performance da estratégia
        
        Returns:
            Dicionário com métricas de performance
        """
        total_trades = self.sinais_corretos + self.sinais_incorretos
        taxa_acerto = (self.sinais_corretos / total_trades * 100) if total_trades > 0 else 0
        
        lucro_liquido = self.lucro_total - self.perda_total
        
        return {
            'nome_estrategia': self.nome,
            'ativa': self.ativa,
            'sinais_gerados': self.sinais_gerados,
            'trades_executados': total_trades,
            'sinais_corretos': self.sinais_corretos,
            'sinais_incorretos': self.sinais_incorretos,
            'taxa_acerto': round(taxa_acerto, 2),
            'lucro_total': float(self.lucro_total),
            'perda_total': float(self.perda_total),
            'lucro_liquido': float(lucro_liquido),
            'ultima_analise': self.ultima_analise,
            'parametros': self.parametros
        }
    
    def ativar(self):
        """Ativa a estratégia"""
        if self.inicializada:
            self.ativa = True
            self.logger.info(f"Estratégia {self.nome} ativada")
        else:
            self.logger.warning(f"Tentativa de ativar estratégia {self.nome} não inicializada")
    
    def desativar(self):
        """Desativa a estratégia"""
        self.ativa = False
        self.logger.info(f"Estratégia {self.nome} desativada")
    
    def _validar_parametros(self) -> bool:
        """
        Valida os parâmetros da estratégia
        
        Returns:
            True se parâmetros são válidos
        """
        try:
            # Validações básicas
            if self.intervalo_analise <= 0:
                return False
            
            if not (0 <= self.min_confianca <= 1):
                return False
            
            if not (0 < self.max_risco_por_trade <= 0.1):  # Máximo 10% de risco
                return False
            
            return self._validar_parametros_especificos()
            
        except Exception as e:
            self.logger.error(f"Erro na validação de parâmetros: {e}")
            return False
    
    def _validar_sinal(self, sinal: SinalTrade) -> bool:
        """
        Valida se o sinal gerado é válido
        
        Args:
            sinal: Sinal a ser validado
            
        Returns:
            True se sinal é válido
        """
        try:
            # Verificar confiança mínima
            if sinal.confianca < self.min_confianca:
                return False
            
            # Verificar se preços são válidos
            if sinal.preco_entrada <= 0:
                return False
            
            # Verificar stop loss e take profit
            if sinal.stop_loss and sinal.stop_loss <= 0:
                return False
            
            if sinal.take_profit and sinal.take_profit <= 0:
                return False
            
            # Verificar razão risco/retorno
            if sinal.razao_risco_retorno < 1.0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação do sinal: {e}")
            return False
    
    # ==================== MÉTODOS ABSTRATOS ====================
    
    @abstractmethod
    async def _inicializar_especifica(self):
        """Inicialização específica da estratégia (deve ser implementada)"""
        pass
    
    @abstractmethod
    async def _finalizar_especifica(self):
        """Finalização específica da estratégia (deve ser implementada)"""
        pass
    
    @abstractmethod
    async def _analisar_especifica(self, dados_mercado: DadosMercado) -> Optional[SinalTrade]:
        """
        Análise específica da estratégia (deve ser implementada)
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Sinal de trading se gerado, None caso contrário
        """
        pass
    
    @abstractmethod
    def _validar_parametros_especificos(self) -> bool:
        """
        Validação específica de parâmetros da estratégia (deve ser implementada)
        
        Returns:
            True se parâmetros específicos são válidos
        """
        pass
    
    # ==================== MÉTODOS UTILITÁRIOS ====================
    
    def calcular_media_movel(self, precos: pd.Series, periodo: int) -> pd.Series:
        """Calcula média móvel simples"""
        return precos.rolling(window=periodo).mean()
    
    def calcular_rsi(self, precos: pd.Series, periodo: int = 14) -> pd.Series:
        """Calcula RSI (Relative Strength Index)"""
        delta = precos.diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
        
        rs = ganho / perda
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calcular_bandas_bollinger(self, precos: pd.Series, periodo: int = 20, 
                                 desvios: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula Bandas de Bollinger"""
        media = precos.rolling(window=periodo).mean()
        std = precos.rolling(window=periodo).std()
        
        banda_superior = media + (std * desvios)
        banda_inferior = media - (std * desvios)
        
        return banda_superior, media, banda_inferior
    
    def calcular_macd(self, precos: pd.Series, rapida: int = 12, 
                     lenta: int = 26, sinal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD"""
        ema_rapida = precos.ewm(span=rapida).mean()
        ema_lenta = precos.ewm(span=lenta).mean()
        
        macd = ema_rapida - ema_lenta
        linha_sinal = macd.ewm(span=sinal).mean()
        histograma = macd - linha_sinal
        
        return macd, linha_sinal, histograma
    
    def __str__(self) -> str:
        """Representação em string da estratégia"""
        return f"{self.__class__.__name__}(nome={self.nome}, ativa={self.ativa})"
    
    def __repr__(self) -> str:
        """Representação detalhada da estratégia"""
        return (f"{self.__class__.__name__}("
                f"nome={self.nome}, "
                f"ativa={self.ativa}, "
                f"inicializada={self.inicializada}, "
                f"sinais_gerados={self.sinais_gerados})")
