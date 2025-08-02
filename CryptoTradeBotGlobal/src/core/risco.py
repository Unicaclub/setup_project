"""
Módulo de Gerenciamento de Risco Avançado
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import obter_logger, log_performance
from src.core.exceptions import ErroRisco, ErroValidacao


class TipoRisco(Enum):
    """Tipos de risco monitorados"""
    STOP_LOSS = "stop_loss"
    DRAWDOWN_MAXIMO = "drawdown_maximo"
    PERDA_DIARIA = "perda_diaria"
    CONCENTRACAO_ATIVO = "concentracao_ativo"
    VOLUME_EXCESSIVO = "volume_excessivo"
    VOLATILIDADE_ALTA = "volatilidade_alta"


class NivelRisco(Enum):
    """Níveis de severidade do risco"""
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


@dataclass
class AlertaRisco:
    """Estrutura para alertas de risco"""
    tipo: TipoRisco
    nivel: NivelRisco
    simbolo: Optional[str]
    valor_atual: float
    limite: float
    percentual: float
    timestamp: datetime
    mensagem: str
    acao_recomendada: str


class GerenciadorRiscoAvancado:
    """
    Gerenciador de Risco Avançado para Trading de Criptomoedas
    
    Funcionalidades:
    - Stop Loss automático
    - Controle de drawdown máximo
    - Limite de perda diária
    - Controle de concentração por ativo
    - Monitoramento de volatilidade
    - Alertas em tempo real
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa o gerenciador de risco
        
        Args:
            configuracao: Configurações de risco
        """
        self.logger = obter_logger(__name__)
        
        # Configurações de risco
        self.stop_loss_percentual = Decimal(str(configuracao.get('stop_loss_percentual', 0.05)))  # 5%
        self.max_drawdown = Decimal(str(configuracao.get('max_drawdown', 0.15)))  # 15%
        self.max_perda_diaria = Decimal(str(configuracao.get('max_perda_diaria', 1000)))  # $1000
        self.max_concentracao_ativo = Decimal(str(configuracao.get('max_concentracao_ativo', 0.3)))  # 30%
        self.max_volume_ordem = Decimal(str(configuracao.get('max_volume_ordem', 5000)))  # $5000
        self.limite_volatilidade = Decimal(str(configuracao.get('limite_volatilidade', 0.1)))  # 10%
        
        # Estado do sistema
        self.ativo = configuracao.get('ativo', True)
        self.modo_emergencia = False
        self.alertas_ativos: List[AlertaRisco] = []
        self.historico_perdas_diarias: Dict[str, Decimal] = {}
        self.posicoes_abertas: Dict[str, Dict] = {}
        self.valor_portfolio_inicial: Optional[Decimal] = None
        self.valor_portfolio_pico: Optional[Decimal] = None
        
        # Estatísticas
        self.total_alertas_gerados = 0
        self.ordens_bloqueadas = 0
        self.stop_losses_executados = 0
        
        self.logger.info("🛡️ Gerenciador de Risco inicializado")
        self.logger.info(f"  • Stop Loss: {float(self.stop_loss_percentual)*100:.1f}%")
        self.logger.info(f"  • Max Drawdown: {float(self.max_drawdown)*100:.1f}%")
        self.logger.info(f"  • Max Perda Diária: ${self.max_perda_diaria}")
        self.logger.info(f"  • Max Concentração: {float(self.max_concentracao_ativo)*100:.1f}%")
    
    @log_performance
    async def validar_ordem(self, ordem: Dict[str, Any], saldos: Dict[str, float], 
                           stats_portfolio: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Valida uma ordem antes da execução
        
        Args:
            ordem: Dados da ordem a ser validada
            saldos: Saldos atuais da conta
            stats_portfolio: Estatísticas do portfolio
            
        Returns:
            Tupla (aprovado, motivo_rejeicao)
        """
        if not self.ativo:
            return True, None
        
        if self.modo_emergencia:
            return False, "Sistema em modo de emergência - trading suspenso"
        
        try:
            simbolo = ordem.get('simbolo', '')
            acao = ordem.get('acao', '')
            quantidade = Decimal(str(ordem.get('quantidade', 0)))
            preco = Decimal(str(ordem.get('preco', 0)))
            valor_ordem = quantidade * preco
            
            # Validação 1: Volume máximo por ordem
            if valor_ordem > self.max_volume_ordem:
                motivo = f"Volume da ordem (${valor_ordem}) excede limite (${self.max_volume_ordem})"
                await self._gerar_alerta(TipoRisco.VOLUME_EXCESSIVO, NivelRisco.ALTO, 
                                       simbolo, float(valor_ordem), float(self.max_volume_ordem), motivo)
                return False, motivo
            
            # Validação 2: Perda diária
            if not await self._validar_perda_diaria(valor_ordem, acao):
                motivo = f"Ordem excederia limite de perda diária (${self.max_perda_diaria})"
                return False, motivo
            
            # Validação 3: Concentração por ativo
            if acao == 'COMPRAR':
                if not await self._validar_concentracao_ativo(simbolo, valor_ordem, stats_portfolio):
                    motivo = f"Ordem excederia concentração máxima em {simbolo} ({float(self.max_concentracao_ativo)*100:.1f}%)"
                    return False, motivo
            
            # Validação 4: Drawdown máximo
            if not await self._validar_drawdown(stats_portfolio):
                motivo = f"Portfolio em drawdown máximo ({float(self.max_drawdown)*100:.1f}%)"
                return False, motivo
            
            # Validação 5: Stop Loss (para ordens de venda)
            if acao == 'VENDER':
                if await self._verificar_stop_loss(simbolo, preco):
                    self.logger.info(f"🛑 Stop Loss ativado para {simbolo} @ ${preco}")
                    self.stop_losses_executados += 1
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de risco: {str(e)}")
            return False, f"Erro interno na validação de risco: {str(e)}"
    
    async def _validar_perda_diaria(self, valor_ordem: Decimal, acao: str) -> bool:
        """Valida se a ordem não excede o limite de perda diária"""
        hoje = datetime.now().strftime('%Y-%m-%d')
        perda_hoje = self.historico_perdas_diarias.get(hoje, Decimal('0'))
        
        # Estimar impacto da ordem (conservador)
        if acao == 'COMPRAR':
            # Compras podem gerar perdas se o preço cair
            impacto_estimado = valor_ordem * self.stop_loss_percentual
        else:
            # Vendas podem ser stop losses
            impacto_estimado = Decimal('0')  # Não penalizar vendas
        
        perda_projetada = perda_hoje + impacto_estimado
        
        if perda_projetada > self.max_perda_diaria:
            await self._gerar_alerta(TipoRisco.PERDA_DIARIA, NivelRisco.CRITICO, 
                                   None, float(perda_projetada), float(self.max_perda_diaria),
                                   f"Perda diária projetada: ${perda_projetada}")
            return False
        
        return True
    
    async def _validar_concentracao_ativo(self, simbolo: str, valor_ordem: Decimal, 
                                        stats_portfolio: Dict[str, Any]) -> bool:
        """Valida concentração máxima por ativo"""
        valor_portfolio = Decimal(str(stats_portfolio.get('valor_portfolio', 0)))
        
        if valor_portfolio == 0:
            return True
        
        # Calcular valor atual do ativo no portfolio
        valor_atual_ativo = Decimal('0')
        if simbolo in self.posicoes_abertas:
            valor_atual_ativo = self.posicoes_abertas[simbolo].get('valor', Decimal('0'))
        
        # Calcular nova concentração
        novo_valor_ativo = valor_atual_ativo + valor_ordem
        nova_concentracao = novo_valor_ativo / valor_portfolio
        
        if nova_concentracao > self.max_concentracao_ativo:
            await self._gerar_alerta(TipoRisco.CONCENTRACAO_ATIVO, NivelRisco.ALTO,
                                   simbolo, float(nova_concentracao), float(self.max_concentracao_ativo),
                                   f"Concentração em {simbolo}: {nova_concentracao*100:.1f}%")
            return False
        
        return True
    
    async def _validar_drawdown(self, stats_portfolio: Dict[str, Any]) -> bool:
        """Valida se o drawdown não excede o limite"""
        valor_atual = Decimal(str(stats_portfolio.get('valor_portfolio', 0)))
        
        # Inicializar valores se necessário
        if self.valor_portfolio_inicial is None:
            self.valor_portfolio_inicial = valor_atual
            self.valor_portfolio_pico = valor_atual
            return True
        
        # Atualizar pico se necessário
        if valor_atual > self.valor_portfolio_pico:
            self.valor_portfolio_pico = valor_atual
        
        # Calcular drawdown atual
        if self.valor_portfolio_pico > 0:
            drawdown_atual = (self.valor_portfolio_pico - valor_atual) / self.valor_portfolio_pico
            
            if drawdown_atual > self.max_drawdown:
                await self._gerar_alerta(TipoRisco.DRAWDOWN_MAXIMO, NivelRisco.CRITICO,
                                       None, float(drawdown_atual), float(self.max_drawdown),
                                       f"Drawdown atual: {drawdown_atual*100:.1f}%")
                
                # Ativar modo de emergência se drawdown for muito alto
                if drawdown_atual > self.max_drawdown * Decimal('1.2'):  # 20% acima do limite
                    self.modo_emergencia = True
                    self.logger.critical("🚨 MODO DE EMERGÊNCIA ATIVADO - Trading suspenso")
                
                return False
        
        return True
    
    async def _verificar_stop_loss(self, simbolo: str, preco_atual: Decimal) -> bool:
        """Verifica se deve executar stop loss"""
        if simbolo not in self.posicoes_abertas:
            return False
        
        posicao = self.posicoes_abertas[simbolo]
        preco_entrada = posicao.get('preco_entrada', Decimal('0'))
        
        if preco_entrada == 0:
            return False
        
        # Calcular perda percentual
        perda_percentual = (preco_entrada - preco_atual) / preco_entrada
        
        if perda_percentual >= self.stop_loss_percentual:
            await self._gerar_alerta(TipoRisco.STOP_LOSS, NivelRisco.ALTO,
                                   simbolo, float(perda_percentual), float(self.stop_loss_percentual),
                                   f"Stop Loss ativado: {perda_percentual*100:.1f}% de perda")
            return True
        
        return False
    
    async def _gerar_alerta(self, tipo: TipoRisco, nivel: NivelRisco, simbolo: Optional[str],
                          valor_atual: float, limite: float, mensagem: str):
        """Gera um alerta de risco"""
        percentual = (valor_atual / limite - 1) * 100 if limite > 0 else 0
        
        alerta = AlertaRisco(
            tipo=tipo,
            nivel=nivel,
            simbolo=simbolo,
            valor_atual=valor_atual,
            limite=limite,
            percentual=percentual,
            timestamp=datetime.now(),
            mensagem=mensagem,
            acao_recomendada=self._obter_acao_recomendada(tipo, nivel)
        )
        
        self.alertas_ativos.append(alerta)
        self.total_alertas_gerados += 1
        
        # Log do alerta
        emoji_nivel = {"baixo": "🟡", "medio": "🟠", "alto": "🔴", "critico": "🚨"}
        emoji = emoji_nivel.get(nivel.value, "⚠️")
        
        self.logger.warning(f"{emoji} ALERTA DE RISCO | {tipo.value.upper()} | {mensagem}")
        
        # Limpar alertas antigos (manter apenas últimos 100)
        if len(self.alertas_ativos) > 100:
            self.alertas_ativos = self.alertas_ativos[-100:]
    
    def _obter_acao_recomendada(self, tipo: TipoRisco, nivel: NivelRisco) -> str:
        """Obtém ação recomendada para um tipo de risco"""
        acoes = {
            TipoRisco.STOP_LOSS: "Executar venda imediata",
            TipoRisco.DRAWDOWN_MAXIMO: "Reduzir exposição e revisar estratégia",
            TipoRisco.PERDA_DIARIA: "Suspender trading até próximo dia",
            TipoRisco.CONCENTRACAO_ATIVO: "Diversificar portfolio",
            TipoRisco.VOLUME_EXCESSIVO: "Reduzir tamanho da ordem",
            TipoRisco.VOLATILIDADE_ALTA: "Aguardar estabilização do mercado"
        }
        
        return acoes.get(tipo, "Revisar parâmetros de risco")
    
    async def atualizar_posicao(self, simbolo: str, acao: str, quantidade: Decimal, 
                              preco: Decimal, timestamp: datetime):
        """
        Atualiza posição após execução de ordem
        
        Args:
            simbolo: Símbolo do ativo
            acao: COMPRAR ou VENDER
            quantidade: Quantidade negociada
            preco: Preço da operação
            timestamp: Timestamp da operação
        """
        try:
            if simbolo not in self.posicoes_abertas:
                self.posicoes_abertas[simbolo] = {
                    'quantidade': Decimal('0'),
                    'valor': Decimal('0'),
                    'preco_entrada': Decimal('0'),
                    'ultima_atualizacao': timestamp
                }
            
            posicao = self.posicoes_abertas[simbolo]
            
            if acao == 'COMPRAR':
                # Calcular novo preço médio
                quantidade_anterior = posicao['quantidade']
                valor_anterior = posicao['valor']
                
                nova_quantidade = quantidade_anterior + quantidade
                novo_valor = valor_anterior + (quantidade * preco)
                
                if nova_quantidade > 0:
                    novo_preco_medio = novo_valor / nova_quantidade
                    posicao['preco_entrada'] = novo_preco_medio
                
                posicao['quantidade'] = nova_quantidade
                posicao['valor'] = novo_valor
                
            elif acao == 'VENDER':
                posicao['quantidade'] -= quantidade
                posicao['valor'] -= (quantidade * preco)
                
                # Se zerou a posição, limpar
                if posicao['quantidade'] <= 0:
                    posicao['quantidade'] = Decimal('0')
                    posicao['valor'] = Decimal('0')
                    posicao['preco_entrada'] = Decimal('0')
            
            posicao['ultima_atualizacao'] = timestamp
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar posição {simbolo}: {str(e)}")
    
    async def registrar_resultado_trade(self, simbolo: str, pnl: Decimal, timestamp: datetime):
        """
        Registra resultado de um trade para controle de perda diária
        
        Args:
            simbolo: Símbolo do ativo
            pnl: Profit & Loss do trade
            timestamp: Timestamp do trade
        """
        try:
            data = timestamp.strftime('%Y-%m-%d')
            
            if data not in self.historico_perdas_diarias:
                self.historico_perdas_diarias[data] = Decimal('0')
            
            # Registrar apenas perdas (PnL negativo)
            if pnl < 0:
                self.historico_perdas_diarias[data] += abs(pnl)
                
                # Verificar se excedeu limite diário
                if self.historico_perdas_diarias[data] > self.max_perda_diaria:
                    await self._gerar_alerta(TipoRisco.PERDA_DIARIA, NivelRisco.CRITICO,
                                           simbolo, float(self.historico_perdas_diarias[data]), 
                                           float(self.max_perda_diaria),
                                           f"Limite de perda diária excedido: ${self.historico_perdas_diarias[data]}")
        
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar resultado do trade: {str(e)}")
    
    async def obter_status_risco(self) -> Dict[str, Any]:
        """
        Obtém status atual do gerenciamento de risco
        
        Returns:
            Dicionário com status de risco
        """
        hoje = datetime.now().strftime('%Y-%m-%d')
        perda_hoje = self.historico_perdas_diarias.get(hoje, Decimal('0'))
        
        # Calcular drawdown atual
        drawdown_atual = Decimal('0')
        if self.valor_portfolio_pico and self.valor_portfolio_inicial:
            valor_atual = self.valor_portfolio_pico  # Usar último valor conhecido
            drawdown_atual = (self.valor_portfolio_pico - valor_atual) / self.valor_portfolio_pico
        
        status = {
            'ativo': self.ativo,
            'modo_emergencia': self.modo_emergencia,
            'configuracao': {
                'stop_loss_percentual': float(self.stop_loss_percentual),
                'max_drawdown': float(self.max_drawdown),
                'max_perda_diaria': float(self.max_perda_diaria),
                'max_concentracao_ativo': float(self.max_concentracao_ativo),
                'max_volume_ordem': float(self.max_volume_ordem)
            },
            'estado_atual': {
                'perda_diaria': float(perda_hoje),
                'drawdown_atual': float(drawdown_atual),
                'posicoes_abertas': len(self.posicoes_abertas),
                'alertas_ativos': len(self.alertas_ativos)
            },
            'estatisticas': {
                'total_alertas_gerados': self.total_alertas_gerados,
                'ordens_bloqueadas': self.ordens_bloqueadas,
                'stop_losses_executados': self.stop_losses_executados
            },
            'alertas_recentes': [
                {
                    'tipo': alerta.tipo.value,
                    'nivel': alerta.nivel.value,
                    'simbolo': alerta.simbolo,
                    'mensagem': alerta.mensagem,
                    'timestamp': alerta.timestamp.isoformat()
                }
                for alerta in self.alertas_ativos[-5:]  # Últimos 5 alertas
            ]
        }
        
        return status
    
    async def ativar_modo_emergencia(self, motivo: str):
        """
        Ativa modo de emergência (suspende trading)
        
        Args:
            motivo: Motivo da ativação
        """
        self.modo_emergencia = True
        self.logger.critical(f"🚨 MODO DE EMERGÊNCIA ATIVADO: {motivo}")
        
        await self._gerar_alerta(TipoRisco.DRAWDOWN_MAXIMO, NivelRisco.CRITICO,
                               None, 0, 0, f"Modo de emergência: {motivo}")
    
    async def desativar_modo_emergencia(self):
        """Desativa modo de emergência"""
        self.modo_emergencia = False
        self.logger.info("✅ Modo de emergência desativado")
    
    async def resetar_perdas_diarias(self):
        """Reseta contador de perdas diárias (usar com cuidado)"""
        self.historico_perdas_diarias.clear()
        self.logger.info("🔄 Histórico de perdas diárias resetado")
    
    async def ajustar_parametros(self, novos_parametros: Dict[str, Any]):
        """
        Ajusta parâmetros de risco em tempo real
        
        Args:
            novos_parametros: Novos parâmetros de risco
        """
        try:
            if 'stop_loss_percentual' in novos_parametros:
                self.stop_loss_percentual = Decimal(str(novos_parametros['stop_loss_percentual']))
            
            if 'max_drawdown' in novos_parametros:
                self.max_drawdown = Decimal(str(novos_parametros['max_drawdown']))
            
            if 'max_perda_diaria' in novos_parametros:
                self.max_perda_diaria = Decimal(str(novos_parametros['max_perda_diaria']))
            
            if 'max_concentracao_ativo' in novos_parametros:
                self.max_concentracao_ativo = Decimal(str(novos_parametros['max_concentracao_ativo']))
            
            self.logger.info("⚙️ Parâmetros de risco atualizados")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao ajustar parâmetros: {str(e)}")
            raise ErroValidacao(f"Parâmetros inválidos: {str(e)}")


# Configuração padrão do gerenciador de risco
CONFIGURACAO_PADRAO_RISCO = {
    'stop_loss_percentual': 0.05,      # 5%
    'max_drawdown': 0.15,              # 15%
    'max_perda_diaria': 1000,          # $1000
    'max_concentracao_ativo': 0.3,     # 30%
    'max_volume_ordem': 5000,          # $5000
    'limite_volatilidade': 0.1,        # 10%
    'ativo': True
}


def criar_gerenciador_risco(configuracao: Optional[Dict[str, Any]] = None) -> GerenciadorRiscoAvancado:
    """
    Cria instância do gerenciador de risco
    
    Args:
        configuracao: Configuração personalizada
        
    Returns:
        Instância do gerenciador de risco
    """
    config = CONFIGURACAO_PADRAO_RISCO.copy()
    if configuracao:
        config.update(configuracao)
    
    return GerenciadorRiscoAvancado(config)


if __name__ == "__main__":
    # Teste do gerenciador de risco
    import asyncio
    
    async def testar_gerenciador_risco():
        """Teste básico do gerenciador de risco"""
        print("🧪 Testando Gerenciador de Risco...")
        
        # Criar gerenciador
        gerenciador = criar_gerenciador_risco()
        
        # Simular validação de ordem
        ordem_teste = {
            'simbolo': 'BTC/USDT',
            'acao': 'COMPRAR',
            'quantidade': 0.1,
            'preco': 50000
        }
        
        saldos_teste = {'USDT': 10000, 'BTC': 0}
        stats_teste = {'valor_portfolio': 10000, 'pnl': 0}
        
        # Validar ordem
        aprovado, motivo = await gerenciador.validar_ordem(ordem_teste, saldos_teste, stats_teste)
        print(f"Ordem aprovada: {aprovado}")
        if motivo:
            print(f"Motivo: {motivo}")
        
        # Obter status
        status = await gerenciador.obter_status_risco()
        print(f"Status: {status['ativo']}, Alertas: {status['estado_atual']['alertas_ativos']}")
        
        print("✅ Teste concluído!")
    
    # Executar teste
    asyncio.run(testar_gerenciador_risco())
