
from decimal import Decimal

# --- RESTAURAÇÃO DA CLASSE GESTORRISCO PARA IMPORTAÇÃO E TESTES ---
class GestorRisco:
    """
    Classe que gerencia risco para ordens: limites de stop-loss e drawdown diário.
    """
    def __init__(self, limite_stop=Decimal('0.05'), limite_drawdown=Decimal('0.10')):
        self.limite_stop = Decimal(limite_stop)
        self.limite_drawdown = Decimal(limite_drawdown)
        self.saldo_inicial = None
        self.saldo_atual = Decimal('0')
        self.saldo_max_historico = Decimal('0')
        self.perda_total = Decimal('0')
        self.ordens_bloqueadas = False
        self._bloqueado = False
        self.perdas_por_posicao = {}
        
    def registrar_saldo(self, valor):
        valor = Decimal(valor)
        if self.saldo_inicial is None:
            self.saldo_inicial = valor
        if valor > self.saldo_max_historico:
            self.saldo_max_historico = valor
        self.saldo_atual = valor
        self._atualizar_perda_total()
        
        # Verificar drawdown
        if self.saldo_max_historico > 0:
            drawdown = 1 - (valor / self.saldo_max_historico)
            if drawdown >= self.limite_drawdown:
                self._bloqueado = True
                
    def registrar_trade(self, simbolo, resultado):
        """Registra resultado de um trade"""
        resultado = Decimal(resultado)
        self.perdas_por_posicao[simbolo] = self.perdas_por_posicao.get(simbolo, Decimal('0')) + resultado
        self.perda_total += resultado
        
        # Verificar stop-loss baseado na perda total
        if self.saldo_inicial and self.perda_total < 0:
            perda_relativa = abs(self.perda_total) / self.saldo_inicial
            if perda_relativa >= self.limite_stop:
                self.ordens_bloqueadas = True
                
    def _atualizar_perda_total(self):
        if self.saldo_inicial is None:
            return
        self.perda_total = self.saldo_atual - self.saldo_inicial
        
        # Verificar stop-loss baseado no saldo atual
        if self.perda_total < 0:
            perda_relativa = abs(self.perda_total) / self.saldo_inicial
            if perda_relativa >= self.limite_stop:
                self.ordens_bloqueadas = True
                
    def pode_operar(self):
        return not self._bloqueado and not self.ordens_bloqueadas
        
    def resetar(self):
        self._bloqueado = False
        self.ordens_bloqueadas = False
        self.perdas_por_posicao = {}
        self.perda_total = Decimal('0')
        if self.saldo_atual > 0:
            self.saldo_max_historico = self.saldo_atual
            
    def status(self):
        return {
            'saldo_inicial': float(self.saldo_inicial) if self.saldo_inicial else None,
            'saldo_atual': float(self.saldo_atual),
            'saldo_max_historico': float(self.saldo_max_historico),
            'perda_total': float(self.perda_total),
            'ordens_bloqueadas': self.ordens_bloqueadas,
            'bloqueado': self._bloqueado,
            'perdas_por_posicao': {k: float(v) for k, v in self.perdas_por_posicao.items()}
        }

"""
Gestor de Risco - CryptoTradeBotGlobal
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json


from src.utils.logger import obter_logger, log_performance
from src.utils.alertas import criar_gerenciador_alertas

# Stub mínimo para evitar NameError nos testes
class AlertaRisco:
    def __init__(self, tipo=None, nivel=None, valor_atual=None, limite=None):
        self.tipo = tipo
        self.nivel = nivel
        self.valor_atual = valor_atual
        self.limite = limite
        from datetime import datetime
        self.timestamp = datetime.now()


class TipoRisco(Enum):
    """Tipos de risco monitorados"""
    DRAWDOWN = "drawdown"
    PERDA_DIARIA = "perda_diaria"
    POSICAO_MAXIMA = "posicao_maxima"
    VOLATILIDADE = "volatilidade"
    CORRELACAO = "correlacao"
    LIQUIDEZ = "liquidez"



# Enum de status de risco com nomes em maiúsculo para compatibilidade

class StatusRisco(Enum):
    NORMAL = "normal"
    ALTO = "alto"
    CRITICO = "critico"


class GestorRiscoCompleto:
    """
    Classe completa de gestão de risco para o sistema de trading
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa o gestor de risco completo
        
        Args:
            config: Configuração do gestor de risco
        """
        self.logger = obter_logger(__name__)
        
        # Configurações padrão
        if config is None:
            config = {}
            
        # Parâmetros de risco
        self.limite_stop = Decimal(str(config.get('limite_stop', '0.05')))
        self.limite_drawdown = Decimal(str(config.get('limite_drawdown', '0.10')))
        
        # Estado atual
        self.saldo_inicial = None
        self.saldo_atual = Decimal('0')
        self.saldo_max_historico = Decimal('0')
        self.perda_total = Decimal('0')
        self.ordens_bloqueadas = False
        self._bloqueado = False
        
        # Sistema de trading
        self.sistema_ativo = True
        self.modo_emergencia = False
        
        # Portfolio
        self.portfolio_atual = Decimal(str(config.get('portfolio_inicial', '10000')))
        self.portfolio_inicial = self.portfolio_atual
        self.pico_portfolio = self.portfolio_atual
        
        # Perdas e riscos
        self.perda_diaria_atual = Decimal('0.0')
        self.data_atual = datetime.now().date()
        
        # Posições e trades
        self.posicoes_ativas = {}
        self.perdas_por_posicao = {}
        
        # Estatísticas
        self.total_alertas_risco = 0
        self.paradas_emergencia = 0
        self.trades_rejeitados = 0
        self.alertas_enviados = []
        
        # Histórico
        self.historico_saldos = []
        self.historico_drawdown = []
        self.historico_perdas_diarias = []
        
        # Parâmetros avançados
        class ParametrosRisco:
            def __init__(self):
                self.drawdown_maximo = Decimal('0.20')
                self.drawdown_alerta = Decimal('0.15')
                self.perda_diaria_maxima = Decimal('1000')
                self.perda_diaria_alerta = Decimal('750')
                self.posicao_maxima_usd = Decimal('5000')
                self.posicao_maxima_percentual = Decimal('0.30')
                self.max_posicoes_simultaneas = 5
                self.stop_loss_padrao = Decimal('0.05')
                self.take_profit_padrao = Decimal('0.10')
        
        self.parametros = ParametrosRisco()
        
        # Alertas manager
        self.alertas_manager = None
        try:
            self.alertas_manager = criar_gerenciador_alertas()
        except Exception as e:
            self.logger.warning(f"Alertas manager não disponível: {e}")

    def registrar_saldo(self, valor):
        """Registra saldo atual e verifica drawdown"""
        valor = Decimal(str(valor))
        if self.saldo_inicial is None:
            self.saldo_inicial = valor
        
        if valor > self.saldo_max_historico:
            self.saldo_max_historico = valor
            
        self.saldo_atual = valor
        self._atualizar_perda_total()

    def _atualizar_perda_total(self):
        if self.saldo_inicial is None or self.saldo_atual is None:
            return
        self.perda_total = self.saldo_atual - self.saldo_inicial
        # Bloqueia ordens se atingir limite de stop-loss OU limite_drawdown
        if self.perda_total < 0:
            perda_relativa = abs(self.perda_total) / self.saldo_inicial
            if perda_relativa >= self.limite_stop or perda_relativa >= self.limite_drawdown:
                self.ordens_bloqueadas = True
                if perda_relativa >= self.limite_stop:
                    self.logger.warning("Stop-loss atingido. Bloqueando novas ordens!")
                if perda_relativa >= self.limite_drawdown:
                    self.logger.warning("Drawdown diário atingido. Bloqueando novas ordens!")

    def pode_operar(self) -> bool:
        """
        Retorna False se ordens estão bloqueadas por drawdown dinâmico ou stop-loss.
        """
        return not self.ordens_bloqueadas

    def resetar(self):
        from decimal import Decimal
        self.ordens_bloqueadas = False
        self.perdas_por_posicao = {}
        self.perda_total = Decimal('0')
        self.saldo_inicial = self.saldo_atual
        self.historico_saldos = []
        self.logger.info("Gestor de risco resetado.")

    def status(self) -> dict:
        return {
            'saldo_inicial': float(self.saldo_inicial) if self.saldo_inicial else None,
            'saldo_atual': float(self.saldo_atual) if self.saldo_atual else None,
            'perda_total': float(self.perda_total),
            'ordens_bloqueadas': self.ordens_bloqueadas,
            'perdas_por_posicao': {k: float(v) for k, v in self.perdas_por_posicao.items()}
        }

    async def ajustar_parametros(self, novos_parametros: Dict[str, Any]):
        try:
            parametros_alterados = []
            for chave, valor in novos_parametros.items():
                if hasattr(self.parametros, chave):
                    valor_anterior = getattr(self.parametros, chave)
                    setattr(self.parametros, chave, Decimal(str(valor)))
                    parametros_alterados.append(f"{chave}: {valor_anterior} → {valor}")
            if parametros_alterados:
                self.logger.info("⚙️ Parâmetros de risco ajustados:")
                for alteracao in parametros_alterados:
                    self.logger.info(f"  • {alteracao}")
                if self.alertas_manager:
                    await self.alertas_manager.alerta_info(
                        "Parâmetros de Risco Ajustados",
                        f"Parâmetros alterados:\n" + "\n".join(parametros_alterados)
                    )
        except Exception as e:
            self.logger.error(f"❌ Erro ao ajustar parâmetros: {str(e)}")

    @log_performance
    async def avaliar_risco_trade(self, simbolo: str, tipo: str, quantidade: Decimal, 
                                 preco: Decimal) -> Tuple[bool, List[str]]:
        """
        Avalia o risco de um trade antes da execução
        
        Args:
            simbolo: Símbolo do ativo
            tipo: Tipo do trade (COMPRAR/VENDER)
            quantidade: Quantidade do trade





            preco: Preço do trade
            
        Returns:
            Tuple[bool, List[str]]: (aprovado, motivos_rejeicao)
        """
        try:
            motivos_rejeicao = []
            
            # Verificar se sistema está ativo
            if not self.sistema_ativo:
                motivos_rejeicao.append("Sistema de trading desativado por risco")
                return False, motivos_rejeicao
            
            # Verificar modo emergência
            if self.modo_emergencia:
                motivos_rejeicao.append("Sistema em modo emergência")
                return False, motivos_rejeicao
            
            # Calcular valor do trade
            valor_trade = quantidade * preco
            
            # Verificar tamanho máximo da posição
            if valor_trade > self.parametros.posicao_maxima_usd:
                motivos_rejeicao.append(f"Valor do trade (${valor_trade}) excede limite máximo (${self.parametros.posicao_maxima_usd})")
            
            # Verificar percentual máximo do portfolio
            percentual_portfolio = valor_trade / self.portfolio_atual
            if percentual_portfolio > self.parametros.posicao_maxima_percentual:
                motivos_rejeicao.append(f"Trade representa {percentual_portfolio:.1%} do portfolio (máximo: {self.parametros.posicao_maxima_percentual:.1%})")
            
            # Verificar número máximo de posições
            if len(self.posicoes_ativas) >= self.parametros.max_posicoes_simultaneas:
                motivos_rejeicao.append(f"Número máximo de posições simultâneas atingido ({self.parametros.max_posicoes_simultaneas})")
            
            # Verificar drawdown atual
            drawdown_atual = await self._calcular_drawdown()
            if drawdown_atual >= self.parametros.drawdown_maximo:
                motivos_rejeicao.append(f"Drawdown atual ({drawdown_atual:.1%}) excede limite máximo ({self.parametros.drawdown_maximo:.1%})")
            
            # Verificar perda diária
            if self.perda_diaria_atual >= self.parametros.perda_diaria_maxima:
                motivos_rejeicao.append(f"Perda diária atual (${self.perda_diaria_atual}) excede limite máximo (${self.parametros.perda_diaria_maxima})")
            
            # Verificar correlação com posições existentes
            if await self._verificar_correlacao_alta(simbolo):
                motivos_rejeicao.append(f"Alta correlação com posições existentes")
            
            aprovado = len(motivos_rejeicao) == 0
            
            if not aprovado:
                self.trades_rejeitados += 1
                self.logger.warning(f"🚫 Trade rejeitado: {simbolo} {tipo} {quantidade} @ {preco}")
                for motivo in motivos_rejeicao:
                    self.logger.warning(f"  • {motivo}")
            
            return aprovado, motivos_rejeicao
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao avaliar risco do trade: {str(e)}")
            return False, [f"Erro interno: {str(e)}"]
    
    @log_performance
    async def atualizar_portfolio(self, novo_valor: Decimal):
        """
        Atualiza o valor do portfolio e monitora riscos
        
        Args:
            novo_valor: Novo valor do portfolio
        """
        try:
            valor_anterior = self.portfolio_atual
            self.portfolio_atual = novo_valor
            
            # Atualizar pico do portfolio
            if novo_valor > self.pico_portfolio:
                self.pico_portfolio = novo_valor
            
            # Calcular mudança
            mudanca = novo_valor - valor_anterior
            
            # Atualizar perda diária
            data_hoje = datetime.now().date()
            if data_hoje != self.data_atual:
                # Novo dia - resetar perda diária
                self.data_atual = data_hoje
                self.perda_diaria_atual = Decimal('0.0')
            
            if mudanca < 0:
                self.perda_diaria_atual += abs(mudanca)
            
            # Verificar alertas de risco
            await self._verificar_alertas_risco()
            
            # Atualizar histórico
            await self._atualizar_historico()
            
            self.logger.debug(f"📊 Portfolio atualizado: ${novo_valor} (mudança: ${mudanca:+})")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar portfolio: {str(e)}")
    
    async def adicionar_posicao(self, simbolo: str, tipo: str, quantidade: Decimal, 
                              preco_entrada: Decimal, stop_loss: Decimal = None, 
                              take_profit: Decimal = None):
        """
        Adiciona uma nova posição ao monitoramento
        
        Args:
            simbolo: Símbolo do ativo
            tipo: Tipo da posição (LONG/SHORT)
            quantidade: Quantidade da posição
            preco_entrada: Preço de entrada
            stop_loss: Preço de stop loss
            take_profit: Preço de take profit
        """
        try:
            # Calcular stop loss e take profit padrão se não fornecidos
            if stop_loss is None:
                if tipo == "LONG":
                    stop_loss = preco_entrada * (1 - self.parametros.stop_loss_padrao)
                else:
                    stop_loss = preco_entrada * (1 + self.parametros.stop_loss_padrao)
            
            if take_profit is None:
                if tipo == "LONG":
                    take_profit = preco_entrada * (1 + self.parametros.take_profit_padrao)
                else:
                    take_profit = preco_entrada * (1 - self.parametros.take_profit_padrao)
            
            posicao = {
                'simbolo': simbolo,
                'tipo': tipo,
                'quantidade': quantidade,
                'preco_entrada': preco_entrada,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'valor_inicial': quantidade * preco_entrada,
                'timestamp_abertura': datetime.now(),
                'pnl_atual': Decimal('0.0')
            }
            
            self.posicoes_ativas[simbolo] = posicao
            
            self.logger.info(f"📈 Posição adicionada: {simbolo} {tipo} {quantidade} @ {preco_entrada}")
            self.logger.info(f"  • Stop Loss: {stop_loss}")
            self.logger.info(f"  • Take Profit: {take_profit}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao adicionar posição: {str(e)}")
    
    async def remover_posicao(self, simbolo: str, preco_saida: Decimal):
        """
        Remove uma posição do monitoramento
        
        Args:
            simbolo: Símbolo do ativo
            preco_saida: Preço de saída
        """
        try:
            if simbolo not in self.posicoes_ativas:
                self.logger.warning(f"⚠️ Tentativa de remover posição inexistente: {simbolo}")
                return
            
            posicao = self.posicoes_ativas[simbolo]
            
            # Calcular P&L final
            if posicao['tipo'] == "LONG":
                pnl = (preco_saida - posicao['preco_entrada']) * posicao['quantidade']
            else:
                pnl = (posicao['preco_entrada'] - preco_saida) * posicao['quantidade']
            
            # Remover posição
            del self.posicoes_ativas[simbolo]
            
            self.logger.info(f"📉 Posição removida: {simbolo}")
            self.logger.info(f"  • P&L: ${pnl:+}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao remover posição: {str(e)}")
    
    async def atualizar_posicoes(self, precos_atuais: Dict[str, Decimal]):
        """
        Atualiza P&L das posições ativas
        
        Args:
            precos_atuais: Dicionário com preços atuais dos símbolos
        """
        try:
            for simbolo, posicao in self.posicoes_ativas.items():
                if simbolo in precos_atuais:
                    preco_atual = precos_atuais[simbolo]
                    
                    # Calcular P&L atual
                    if posicao['tipo'] == "LONG":
                        pnl = (preco_atual - posicao['preco_entrada']) * posicao['quantidade']
                    else:
                        pnl = (posicao['preco_entrada'] - preco_atual) * posicao['quantidade']
                    
                    posicao['pnl_atual'] = pnl
                    
                    # Verificar stop loss e take profit
                    await self._verificar_stop_loss_take_profit(simbolo, preco_atual)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar posições: {str(e)}")
    
    async def _calcular_drawdown(self) -> Decimal:
        """Calcula o drawdown atual"""
        if self.pico_portfolio == 0:
            return Decimal('0.0')
        
        drawdown = (self.pico_portfolio - self.portfolio_atual) / self.pico_portfolio
        return max(drawdown, Decimal('0.0'))
    
    async def _verificar_alertas_risco(self):
        """Verifica e envia alertas de risco"""
        try:
            alertas = []
            
            # Verificar drawdown
            drawdown_atual = await self._calcular_drawdown()
            
            if drawdown_atual >= self.parametros.drawdown_maximo:
                alertas.append(AlertaRisco(
                    tipo=TipoRisco.DRAWDOWN,
                    nivel=StatusRisco.CRITICO,
                    valor_atual=drawdown_atual,
                    limite=self.parametros.drawdown_maximo
                ))
            elif drawdown_atual >= self.parametros.drawdown_alerta:
                alertas.append(AlertaRisco(
                    tipo=TipoRisco.DRAWDOWN,
                    nivel=StatusRisco.ALTO,
                    valor_atual=drawdown_atual,
                    limite=self.parametros.drawdown_alerta
                ))
            
            # Verificar perda diária
            if self.perda_diaria_atual >= self.parametros.perda_diaria_maxima:
                alertas.append(AlertaRisco(
                    tipo=TipoRisco.PERDA_DIARIA,
                    nivel=StatusRisco.CRITICO,
                    valor_atual=self.perda_diaria_atual,
                    limite=self.parametros.perda_diaria_maxima
                ))
            elif self.perda_diaria_atual >= self.parametros.perda_diaria_alerta:
                alertas.append(AlertaRisco(
                    tipo=TipoRisco.PERDA_DIARIA,
                    nivel=StatusRisco.ALTO,
                    valor_atual=self.perda_diaria_atual,
                    limite=self.parametros.perda_diaria_alerta
                ))
            
            # Processar alertas
            for alerta in alertas:
                await self._processar_alerta_risco(alerta)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar alertas de risco: {str(e)}")
    
    async def _processar_alerta_risco(self, alerta: AlertaRisco):
        """Processa um alerta de risco"""
        try:
            self.alertas_enviados.append(alerta)
            self.total_alertas_risco += 1
            
            # Log do alerta
            if alerta.nivel == StatusRisco.CRITICO:
                self.logger.critical(f"🚨 ALERTA CRÍTICO DE RISCO: {alerta.tipo.value}")
                self.logger.critical(f"  • Valor atual: {alerta.valor_atual}")
                self.logger.critical(f"  • Limite: {alerta.limite}")
            else:
                self.logger.warning(f"⚠️ Alerta de risco: {alerta.tipo.value}")
                self.logger.warning(f"  • Valor atual: {alerta.valor_atual}")
                self.logger.warning(f"  • Limite: {alerta.limite}")
            
            # Enviar alerta via sistema de alertas
            if self.alertas_manager:
                titulo = f"Alerta de Risco - {alerta.tipo.value.title()}"
                mensagem = f"Nível: {alerta.nivel.value.upper()}\n"
                mensagem += f"Valor atual: {alerta.valor_atual}\n"
                mensagem += f"Limite: {alerta.limite}"
                
                dados_extras = {
                    'tipo_risco': alerta.tipo.value,
                    'nivel': alerta.nivel.value,
                    'valor_atual': str(alerta.valor_atual),
                    'limite': str(alerta.limite),
                    'portfolio_atual': str(self.portfolio_atual)
                }
                
                if alerta.nivel == StatusRisco.CRITICO:
                    await self.alertas_manager.alerta_critical(titulo, mensagem, dados_extras)
                else:
                    await self.alertas_manager.alerta_risco(titulo, mensagem, dados_extras)
            
            # Ações automáticas para alertas críticos
            if alerta.nivel == StatusRisco.CRITICO:
                await self._ativar_modo_emergencia(alerta)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar alerta de risco: {str(e)}")
    
    async def _ativar_modo_emergencia(self, alerta: AlertaRisco):
        """Ativa modo emergência do sistema"""
        try:
            self.modo_emergencia = True
            self.paradas_emergencia += 1
            
            self.logger.critical("🚨 MODO EMERGÊNCIA ATIVADO")
            self.logger.critical(f"  • Motivo: {alerta.tipo.value}")
            self.logger.critical("  • Todas as operações de trading foram suspensas")
            
            # Fechar todas as posições (se configurado)
            # await self._fechar_todas_posicoes()
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao ativar modo emergência: {str(e)}")
    
    async def _verificar_correlacao_alta(self, simbolo: str) -> bool:
        """Verifica se há alta correlação com posições existentes"""
        # Implementação simplificada - em produção, usar dados históricos reais
        simbolos_correlacionados = {
            'BTC/USDT': ['ETH/USDT'],
            'ETH/USDT': ['BTC/USDT'],
        }
        
        simbolos_ativos = set(self.posicoes_ativas.keys())
        simbolos_correlatos = set(simbolos_correlacionados.get(simbolo, []))
        
        return len(simbolos_ativos.intersection(simbolos_correlatos)) > 0
    
    async def _verificar_stop_loss_take_profit(self, simbolo: str, preco_atual: Decimal):
        """Verifica se stop loss ou take profit foram atingidos"""
        try:
            posicao = self.posicoes_ativas[simbolo]
            
            atingiu_stop = False
            atingiu_take_profit = False
            
            if posicao['tipo'] == "LONG":
                atingiu_stop = preco_atual <= posicao['stop_loss']
                atingiu_take_profit = preco_atual >= posicao['take_profit']
            else:
                atingiu_stop = preco_atual >= posicao['stop_loss']
                atingiu_take_profit = preco_atual <= posicao['take_profit']
            
            if atingiu_stop:
                self.logger.warning(f"🛑 Stop Loss atingido: {simbolo} @ {preco_atual}")
                # Aqui seria enviado sinal para fechar posição
                
            elif atingiu_take_profit:
                self.logger.info(f"🎯 Take Profit atingido: {simbolo} @ {preco_atual}")
                # Aqui seria enviado sinal para fechar posição
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar stop loss/take profit: {str(e)}")
    
    async def _atualizar_historico(self):
        """Atualiza histórico de riscos"""
        try:
            agora = datetime.now()
            
            # Histórico de drawdown
            drawdown_atual = await self._calcular_drawdown()
            self.historico_drawdown.append({
                'timestamp': agora,
                'drawdown': float(drawdown_atual),
                'portfolio_valor': float(self.portfolio_atual),
                'pico_portfolio': float(self.pico_portfolio)
            })
            
            # Manter apenas últimos 1000 registros
            if len(self.historico_drawdown) > 1000:
                self.historico_drawdown = self.historico_drawdown[-1000:]
            
            # Histórico de perdas diárias
            if agora.hour == 0 and agora.minute == 0:  # Meia-noite
                self.historico_perdas_diarias.append({
                    'data': agora.date(),
                    'perda_diaria': float(self.perda_diaria_atual)
                })
                
                # Manter apenas últimos 30 dias
                if len(self.historico_perdas_diarias) > 30:
                    self.historico_perdas_diarias = self.historico_perdas_diarias[-30:]
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar histórico: {str(e)}")
    
    async def obter_status_risco(self) -> Dict[str, Any]:
        """
        Obtém status atual do sistema de risco
        
        Returns:
            Dicionário com status completo do risco
        """
        try:
            drawdown_atual = await self._calcular_drawdown()
            
            # Calcular P&L total das posições
            pnl_total_posicoes = sum(pos['pnl_atual'] for pos in self.posicoes_ativas.values())
            
            return {
                'sistema_ativo': self.sistema_ativo,
                'modo_emergencia': self.modo_emergencia,
                'portfolio': {
                    'valor_atual': float(self.portfolio_atual),
                    'valor_inicial': float(self.portfolio_inicial),
                    'pico_valor': float(self.pico_portfolio),
                    'pnl_total': float(self.portfolio_atual - self.portfolio_inicial),
                    'pnl_percentual': float((self.portfolio_atual - self.portfolio_inicial) / self.portfolio_inicial * 100)
                },
                'drawdown': {
                    'atual': float(drawdown_atual),
                    'limite_alerta': float(self.parametros.drawdown_alerta),
                    'limite_maximo': float(self.parametros.drawdown_maximo),
                    'status': 'CRÍTICO' if drawdown_atual >= self.parametros.drawdown_maximo else 
                             'ALTO' if drawdown_atual >= self.parametros.drawdown_alerta else 'NORMAL'
                },
                'perda_diaria': {
                    'atual': float(self.perda_diaria_atual),
                    'limite_alerta': float(self.parametros.perda_diaria_alerta),
                    'limite_maximo': float(self.parametros.perda_diaria_maxima),
                    'data': self.data_atual.isoformat(),
                    'status': 'CRÍTICO' if self.perda_diaria_atual >= self.parametros.perda_diaria_maxima else
                             'ALTO' if self.perda_diaria_atual >= self.parametros.perda_diaria_alerta else 'NORMAL'
                },
                'posicoes': {
                    'total_ativas': len(self.posicoes_ativas),
                    'limite_maximo': self.parametros.max_posicoes_simultaneas,
                    'pnl_total': float(pnl_total_posicoes),
                    'detalhes': [
                        {
                            'simbolo': pos['simbolo'],
                            'tipo': pos['tipo'],
                            'quantidade': float(pos['quantidade']),
                            'preco_entrada': float(pos['preco_entrada']),
                            'pnl_atual': float(pos['pnl_atual']),
                            'stop_loss': float(pos['stop_loss']),
                            'take_profit': float(pos['take_profit'])
                        }
                        for pos in self.posicoes_ativas.values()
                    ]
                },
                'parametros': {
                    'drawdown_maximo': float(self.parametros.drawdown_maximo),
                    'perda_diaria_maxima': float(self.parametros.perda_diaria_maxima),
                    'posicao_maxima_usd': float(self.parametros.posicao_maxima_usd),
                    'stop_loss_padrao': float(self.parametros.stop_loss_padrao),
                    'take_profit_padrao': float(self.parametros.take_profit_padrao)
                },
                'estatisticas': {
                    'total_alertas_risco': self.total_alertas_risco,
                    'paradas_emergencia': self.paradas_emergencia,
                    'trades_rejeitados': self.trades_rejeitados,
                    'alertas_recentes': len([a for a in self.alertas_enviados if 
                                           (datetime.now() - a.timestamp).total_seconds() < 3600])
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter status de risco: {str(e)}")
            return {'erro': str(e)}
    
    async def resetar_modo_emergencia(self):
        """Reseta o modo emergência (uso manual)"""
        try:
            self.modo_emergencia = False
            self.logger.info("✅ Modo emergência resetado manualmente")
            
            if self.alertas_manager:
                await self.alertas_manager.alerta_info(
                    "Modo Emergência Resetado",
                    "O modo emergência foi resetado manualmente. Sistema voltando ao normal."
                )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao resetar modo emergência: {str(e)}")
    
    async def ajustar_parametros(self, novos_parametros: Dict[str, Any]):
        """
        Ajusta parâmetros de risco em tempo real
        
        Args:
            novos_parametros: Dicionário com novos parâmetros
        """
        try:
            parametros_alterados = []
            
            for chave, valor in novos_parametros.items():
                if hasattr(self.parametros, chave):
                    valor_anterior = getattr(self.parametros, chave)
                    setattr(self.parametros, chave, Decimal(str(valor)))
                    parametros_alterados.append(f"{chave}: {valor_anterior} → {valor}")
            
            if parametros_alterados:
                self.logger.info("⚙️ Parâmetros de risco ajustados:")
                for alteracao in parametros_alterados:
                    self.logger.info(f"  • {alteracao}")
                
                if self.alertas_manager:
                    await self.alertas_manager.alerta_info(
                        "Parâmetros de Risco Ajustados",
                        f"Parâmetros alterados:\n" + "\n".join(parametros_alterados)
                    )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao ajustar parâmetros: {str(e)}")







def criar_gestor_risco(config: Dict[str, Any] = None) -> 'GestorRisco':
    """
    Cria instância do gestor de risco
    
    Args:
        config: Configuração do gestor de risco
        
    Returns:
        Instância do gestor de risco
    """
    if config is None:
        config = {}
    return GestorRisco(**config)


# Alias para compatibilidade com código existente
GerenciadorRisco = GestorRisco
