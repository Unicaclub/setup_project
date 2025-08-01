"""
Estratégia Base Simplificada para CryptoTradeBotGlobal
Classe abstrata base para todas as estratégias de trading
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime


class BaseStrategy(ABC):
    """
    Classe base abstrata simplificada para todas as estratégias de trading
    
    Define a interface comum que todas as estratégias devem implementar
    para garantir consistência e intercambiabilidade.
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa a estratégia base
        
        Args:
            configuracao: Configurações da estratégia
        """
        self.configuracao = configuracao
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Estado da estratégia
        self.ativa = False
        self.inicializada = False
        self.ultima_analise = None
        
        # Métricas de performance
        self.sinais_gerados = 0
        self.sinais_corretos = 0
        self.sinais_incorretos = 0
        
        # Configurações padrão
        self.nome = configuracao.get('nome', self.__class__.__name__)
        self.intervalo_analise = configuracao.get('intervalo_analise', 60)  # segundos
        self.min_confianca = configuracao.get('min_confianca', 0.6)
        
        # Histórico de sinais
        self.historico_sinais: List[Dict[str, Any]] = []
    
    async def inicializar(self) -> bool:
        """
        Inicializa a estratégia
        
        Returns:
            True se inicializada com sucesso
        """
        try:
            self.logger.info(f"Inicializando estratégia {self.nome}")
            
            # Validar configuração
            if not self._validar_configuracao():
                raise ValueError("Configuração inválida")
            
            # Inicialização específica da estratégia
            await self._inicializar_especifica()
            
            self.inicializada = True
            self.ativa = True
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
    
    async def analisar(self, dados_mercado: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Análise principal da estratégia
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Lista de sinais de trading gerados
        """
        if not self.inicializada or not self.ativa:
            return []
        
        try:
            self.ultima_analise = datetime.now()
            
            # Análise específica da estratégia
            sinais = await self._analisar_especifica(dados_mercado)
            
            # Validar e processar sinais
            sinais_validos = []
            for sinal in sinais:
                if self._validar_sinal(sinal):
                    self.sinais_gerados += 1
                    self.historico_sinais.append(sinal)
                    sinais_validos.append(sinal)
                    
                    # Limitar histórico
                    if len(self.historico_sinais) > 1000:
                        self.historico_sinais.pop(0)
                    
                    self.logger.info(f"Sinal gerado: {sinal.get('acao', 'DESCONHECIDO')} {sinal.get('simbolo', '')}")
            
            return sinais_validos
            
        except Exception as e:
            self.logger.error(f"Erro na análise da estratégia {self.nome}: {e}")
            return []
    
    def obter_metricas_performance(self) -> Dict[str, Any]:
        """
        Obtém métricas de performance da estratégia
        
        Returns:
            Dicionário com métricas de performance
        """
        total_trades = self.sinais_corretos + self.sinais_incorretos
        taxa_acerto = (self.sinais_corretos / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'nome_estrategia': self.nome,
            'ativa': self.ativa,
            'inicializada': self.inicializada,
            'sinais_gerados': self.sinais_gerados,
            'trades_executados': total_trades,
            'sinais_corretos': self.sinais_corretos,
            'sinais_incorretos': self.sinais_incorretos,
            'taxa_acerto': round(taxa_acerto, 2),
            'ultima_analise': self.ultima_analise.isoformat() if self.ultima_analise else None,
            'configuracao': self.configuracao
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
    
    def _validar_configuracao(self) -> bool:
        """
        Valida a configuração da estratégia
        
        Returns:
            True se configuração é válida
        """
        try:
            # Validações básicas
            if self.intervalo_analise <= 0:
                self.logger.error("Intervalo de análise deve ser positivo")
                return False
            
            if not (0 <= self.min_confianca <= 1):
                self.logger.error("Confiança mínima deve estar entre 0 e 1")
                return False
            
            return self._validar_configuracao_especifica()
            
        except Exception as e:
            self.logger.error(f"Erro na validação da configuração: {e}")
            return False
    
    def _validar_sinal(self, sinal: Dict[str, Any]) -> bool:
        """
        Valida se o sinal gerado é válido
        
        Args:
            sinal: Sinal a ser validado
            
        Returns:
            True se sinal é válido
        """
        try:
            # Verificar campos obrigatórios
            campos_obrigatorios = ['simbolo', 'acao', 'preco', 'timestamp']
            for campo in campos_obrigatorios:
                if campo not in sinal:
                    self.logger.warning(f"Campo obrigatório '{campo}' ausente no sinal")
                    return False
            
            # Verificar confiança mínima
            confianca = sinal.get('confianca', 0.5)
            if confianca < self.min_confianca:
                self.logger.debug(f"Sinal rejeitado por baixa confiança: {confianca}")
                return False
            
            # Verificar se preço é válido
            preco = sinal.get('preco', 0)
            if preco <= 0:
                self.logger.warning("Preço do sinal deve ser positivo")
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
    async def _analisar_especifica(self, dados_mercado: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Análise específica da estratégia (deve ser implementada)
        
        Args:
            dados_mercado: Dados de mercado para análise
            
        Returns:
            Lista de sinais de trading gerados
        """
        pass
    
    @abstractmethod
    def _validar_configuracao_especifica(self) -> bool:
        """
        Validação específica de configuração da estratégia (deve ser implementada)
        
        Returns:
            True se configuração específica é válida
        """
        pass
    
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
