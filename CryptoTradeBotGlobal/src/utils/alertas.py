"""
Sistema de Alertas - CryptoTradeBotGlobal
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import asyncio
import aiohttp
import smtplib
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import obter_logger, log_performance


class TipoAlerta(Enum):
    """Tipos de alerta disponíveis"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    TRADE = "trade"
    RISCO = "risco"


class CanalAlerta(Enum):
    """Canais de envio de alertas"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    DISCORD = "discord"
    WEBHOOK = "webhook"


@dataclass
class Alerta:
    """Estrutura de um alerta"""
    tipo: TipoAlerta
    titulo: str
    mensagem: str
    timestamp: datetime
    dados_extras: Optional[Dict[str, Any]] = None
    urgente: bool = False


class GerenciadorAlertas:
    """
    Gerenciador de alertas para múltiplos canais
    Suporta Telegram, Email, Discord e Webhooks
    """
    
    def __init__(self, configuracao: Dict[str, Any]):
        """
        Inicializa o gerenciador de alertas
        
        Args:
            configuracao: Configurações dos canais de alerta
        """
        self.logger = obter_logger(__name__)
        
        # Configurações
        self.ativo = configuracao.get('ativo', True)
        self.canais_ativos = configuracao.get('canais_ativos', [])
        
        # Configurações Telegram
        self.telegram_token = configuracao.get('telegram_token', '')
        self.telegram_chat_id = configuracao.get('telegram_chat_id', '')
        
        # Configurações Email
        self.email_smtp_server = configuracao.get('email_smtp_server', 'smtp.gmail.com')
        self.email_smtp_port = configuracao.get('email_smtp_port', 587)
        self.email_usuario = configuracao.get('email_usuario', '')
        self.email_senha = configuracao.get('email_senha', '')
        self.email_destinatarios = configuracao.get('email_destinatarios', [])
        
        # Configurações Discord
        self.discord_webhook_url = configuracao.get('discord_webhook_url', '')
        
        # Configurações Webhook personalizado
        self.webhook_url = configuracao.get('webhook_url', '')
        self.webhook_headers = configuracao.get('webhook_headers', {})
        
        # Filtros de alerta
        self.tipos_permitidos = configuracao.get('tipos_permitidos', list(TipoAlerta))
        self.horario_silencioso = configuracao.get('horario_silencioso', False)
        self.horario_inicio_silencio = configuracao.get('horario_inicio_silencio', '22:00')
        self.horario_fim_silencio = configuracao.get('horario_fim_silencio', '08:00')
        
        # Estatísticas
        self.total_alertas_enviados = 0
        self.alertas_por_tipo = {tipo: 0 for tipo in TipoAlerta}
        self.alertas_por_canal = {canal: 0 for canal in CanalAlerta}
        self.falhas_envio = 0
        
        self.logger.info("📢 Gerenciador de Alertas inicializado")
        self.logger.info(f"  • Canais ativos: {', '.join(self.canais_ativos)}")
        self.logger.info(f"  • Tipos permitidos: {len(self.tipos_permitidos)}")
    
    @log_performance
    async def enviar_alerta(self, alerta: Alerta) -> bool:
        """
        Envia um alerta através dos canais configurados
        
        Args:
            alerta: Alerta a ser enviado
            
        Returns:
            True se enviado com sucesso em pelo menos um canal
        """
        if not self.ativo:
            return False
        
        # Verificar filtros
        if not self._deve_enviar_alerta(alerta):
            return False
        
        try:
            sucesso_geral = False
            
            # Enviar para cada canal ativo
            for canal in self.canais_ativos:
                try:
                    if canal == CanalAlerta.TELEGRAM.value:
                        sucesso = await self._enviar_telegram(alerta)
                    elif canal == CanalAlerta.EMAIL.value:
                        sucesso = await self._enviar_email(alerta)
                    elif canal == CanalAlerta.DISCORD.value:
                        sucesso = await self._enviar_discord(alerta)
                    elif canal == CanalAlerta.WEBHOOK.value:
                        sucesso = await self._enviar_webhook(alerta)
                    else:
                        continue
                    
                    if sucesso:
                        sucesso_geral = True
                        self.alertas_por_canal[CanalAlerta(canal)] += 1
                        self.logger.debug(f"✅ Alerta enviado via {canal}")
                    else:
                        self.logger.warning(f"⚠️ Falha ao enviar alerta via {canal}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Erro ao enviar alerta via {canal}: {str(e)}")
                    self.falhas_envio += 1
            
            if sucesso_geral:
                self.total_alertas_enviados += 1
                self.alertas_por_tipo[alerta.tipo] += 1
                self.logger.info(f"📢 Alerta enviado: {alerta.titulo}")
            
            return sucesso_geral
            
        except Exception as e:
            self.logger.error(f"❌ Erro geral no envio de alerta: {str(e)}")
            return False
    
    def _deve_enviar_alerta(self, alerta: Alerta) -> bool:
        """Verifica se o alerta deve ser enviado baseado nos filtros"""
        try:
            # Verificar tipo permitido
            if alerta.tipo not in self.tipos_permitidos:
                return False
            
            # Verificar horário silencioso
            if self.horario_silencioso and not alerta.urgente:
                agora = datetime.now().time()
                inicio = datetime.strptime(self.horario_inicio_silencio, '%H:%M').time()
                fim = datetime.strptime(self.horario_fim_silencio, '%H:%M').time()
                
                if inicio <= agora <= fim:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar filtros: {str(e)}")
            return True  # Em caso de erro, enviar o alerta
    
    async def _enviar_telegram(self, alerta: Alerta) -> bool:
        """Envia alerta via Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        
        try:
            # Formatar mensagem
            emoji_tipo = {
                TipoAlerta.INFO: "ℹ️",
                TipoAlerta.WARNING: "⚠️",
                TipoAlerta.ERROR: "❌",
                TipoAlerta.CRITICAL: "🚨",
                TipoAlerta.TRADE: "💹",
                TipoAlerta.RISCO: "🛡️"
            }
            
            emoji = emoji_tipo.get(alerta.tipo, "📢")
            
            mensagem = f"{emoji} *{alerta.titulo}*\n\n"
            mensagem += f"{alerta.mensagem}\n\n"
            mensagem += f"🕐 {alerta.timestamp.strftime('%d/%m/%Y %H:%M:%S')}"
            
            if alerta.dados_extras:
                mensagem += "\n\n📊 *Dados Adicionais:*\n"
                for chave, valor in alerta.dados_extras.items():
                    mensagem += f"• {chave}: {valor}\n"
            
            # URL da API do Telegram
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': mensagem,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        self.logger.error(f"❌ Erro Telegram: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar Telegram: {str(e)}")
            return False
    
    async def _enviar_email(self, alerta: Alerta) -> bool:
        """Envia alerta via Email"""
        if not self.email_usuario or not self.email_senha or not self.email_destinatarios:
            return False
        
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.email_usuario
            msg['To'] = ', '.join(self.email_destinatarios)
            msg['Subject'] = f"[CryptoTradeBotGlobal] {alerta.titulo}"
            
            # Corpo do email
            corpo = f"""
            <html>
            <body>
                <h2>{alerta.titulo}</h2>
                <p><strong>Tipo:</strong> {alerta.tipo.value.upper()}</p>
                <p><strong>Timestamp:</strong> {alerta.timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
                <hr>
                <p>{alerta.mensagem}</p>
            """
            
            if alerta.dados_extras:
                corpo += "<h3>Dados Adicionais:</h3><ul>"
                for chave, valor in alerta.dados_extras.items():
                    corpo += f"<li><strong>{chave}:</strong> {valor}</li>"
                corpo += "</ul>"
            
            corpo += """
                <hr>
                <p><em>Este é um alerta automático do CryptoTradeBotGlobal</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(corpo, 'html'))
            
            # Enviar email
            server = smtplib.SMTP(self.email_smtp_server, self.email_smtp_port)
            server.starttls()
            server.login(self.email_usuario, self.email_senha)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar email: {str(e)}")
            return False
    
    async def _enviar_discord(self, alerta: Alerta) -> bool:
        """Envia alerta via Discord Webhook"""
        if not self.discord_webhook_url:
            return False
        
        try:
            # Cores por tipo de alerta
            cores = {
                TipoAlerta.INFO: 0x3498db,      # Azul
                TipoAlerta.WARNING: 0xf39c12,   # Laranja
                TipoAlerta.ERROR: 0xe74c3c,     # Vermelho
                TipoAlerta.CRITICAL: 0x8e44ad,  # Roxo
                TipoAlerta.TRADE: 0x2ecc71,     # Verde
                TipoAlerta.RISCO: 0xf1c40f      # Amarelo
            }
            
            embed = {
                "title": alerta.titulo,
                "description": alerta.mensagem,
                "color": cores.get(alerta.tipo, 0x95a5a6),
                "timestamp": alerta.timestamp.isoformat(),
                "footer": {
                    "text": "CryptoTradeBotGlobal"
                },
                "fields": []
            }
            
            # Adicionar dados extras como fields
            if alerta.dados_extras:
                for chave, valor in alerta.dados_extras.items():
                    embed["fields"].append({
                        "name": chave,
                        "value": str(valor),
                        "inline": True
                    })
            
            payload = {
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=payload) as response:
                    if response.status == 204:
                        return True
                    else:
                        self.logger.error(f"❌ Erro Discord: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar Discord: {str(e)}")
            return False
    
    async def _enviar_webhook(self, alerta: Alerta) -> bool:
        """Envia alerta via Webhook personalizado"""
        if not self.webhook_url:
            return False
        
        try:
            payload = {
                "tipo": alerta.tipo.value,
                "titulo": alerta.titulo,
                "mensagem": alerta.mensagem,
                "timestamp": alerta.timestamp.isoformat(),
                "urgente": alerta.urgente,
                "dados_extras": alerta.dados_extras
            }
            
            headers = {
                'Content-Type': 'application/json',
                **self.webhook_headers
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, headers=headers) as response:
                    if 200 <= response.status < 300:
                        return True
                    else:
                        self.logger.error(f"❌ Erro Webhook: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar Webhook: {str(e)}")
            return False
    
    # Métodos de conveniência para diferentes tipos de alerta
    async def alerta_info(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None):
        """Envia alerta de informação"""
        alerta = Alerta(
            tipo=TipoAlerta.INFO,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras
        )
        return await self.enviar_alerta(alerta)
    
    async def alerta_warning(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None):
        """Envia alerta de aviso"""
        alerta = Alerta(
            tipo=TipoAlerta.WARNING,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras
        )
        return await self.enviar_alerta(alerta)
    
    async def alerta_error(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None):
        """Envia alerta de erro"""
        alerta = Alerta(
            tipo=TipoAlerta.ERROR,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras
        )
        return await self.enviar_alerta(alerta)
    
    async def alerta_critical(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None, urgente: bool = True):
        """Envia alerta crítico"""
        alerta = Alerta(
            tipo=TipoAlerta.CRITICAL,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras,
            urgente=urgente
        )
        return await self.enviar_alerta(alerta)
    
    async def alerta_trade(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None):
        """Envia alerta de trade"""
        alerta = Alerta(
            tipo=TipoAlerta.TRADE,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras
        )
        return await self.enviar_alerta(alerta)
    
    async def alerta_risco(self, titulo: str, mensagem: str, dados_extras: Optional[Dict] = None, urgente: bool = True):
        """Envia alerta de risco"""
        alerta = Alerta(
            tipo=TipoAlerta.RISCO,
            titulo=titulo,
            mensagem=mensagem,
            timestamp=datetime.now(),
            dados_extras=dados_extras,
            urgente=urgente
        )
        return await self.enviar_alerta(alerta)
    
    async def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do sistema de alertas
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            'ativo': self.ativo,
            'canais_ativos': self.canais_ativos,
            'total_alertas_enviados': self.total_alertas_enviados,
            'falhas_envio': self.falhas_envio,
            'taxa_sucesso': (self.total_alertas_enviados / max(self.total_alertas_enviados + self.falhas_envio, 1)) * 100,
            'alertas_por_tipo': {tipo.value: count for tipo, count in self.alertas_por_tipo.items()},
            'alertas_por_canal': {canal.value: count for canal, count in self.alertas_por_canal.items()},
            'configuracao': {
                'horario_silencioso': self.horario_silencioso,
                'tipos_permitidos': [tipo.value for tipo in self.tipos_permitidos],
                'telegram_configurado': bool(self.telegram_token and self.telegram_chat_id),
                'email_configurado': bool(self.email_usuario and self.email_senha),
                'discord_configurado': bool(self.discord_webhook_url),
                'webhook_configurado': bool(self.webhook_url)
            }
        }
    
    async def testar_canais(self) -> Dict[str, bool]:
        """
        Testa todos os canais configurados
        
        Returns:
            Dicionário com resultado dos testes
        """
        resultados = {}
        
        alerta_teste = Alerta(
            tipo=TipoAlerta.INFO,
            titulo="Teste do Sistema de Alertas",
            mensagem="Este é um teste automático do sistema de alertas do CryptoTradeBotGlobal.",
            timestamp=datetime.now(),
            dados_extras={"teste": True, "versao": "1.0.0"}
        )
        
        for canal in self.canais_ativos:
            try:
                if canal == CanalAlerta.TELEGRAM.value:
                    resultado = await self._enviar_telegram(alerta_teste)
                elif canal == CanalAlerta.EMAIL.value:
                    resultado = await self._enviar_email(alerta_teste)
                elif canal == CanalAlerta.DISCORD.value:
                    resultado = await self._enviar_discord(alerta_teste)
                elif canal == CanalAlerta.WEBHOOK.value:
                    resultado = await self._enviar_webhook(alerta_teste)
                else:
                    resultado = False
                
                resultados[canal] = resultado
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao testar canal {canal}: {str(e)}")
                resultados[canal] = False
        
        return resultados


# Configuração padrão do sistema de alertas
CONFIGURACAO_PADRAO_ALERTAS = {
    'ativo': True,
    'canais_ativos': [],
    'telegram_token': '',
    'telegram_chat_id': '',
    'email_smtp_server': 'smtp.gmail.com',
    'email_smtp_port': 587,
    'email_usuario': '',
    'email_senha': '',
    'email_destinatarios': [],
    'discord_webhook_url': '',
    'webhook_url': '',
    'webhook_headers': {},
    'tipos_permitidos': list(TipoAlerta),
    'horario_silencioso': False,
    'horario_inicio_silencio': '22:00',
    'horario_fim_silencio': '08:00'
}


def criar_gerenciador_alertas(configuracao: Optional[Dict[str, Any]] = None) -> GerenciadorAlertas:
    """
    Cria instância do gerenciador de alertas
    
    Args:
        configuracao: Configuração personalizada
        
    Returns:
        Instância do gerenciador de alertas
    """
    config = CONFIGURACAO_PADRAO_ALERTAS.copy()
    if configuracao:
        config.update(configuracao)
    
    # Carregar configurações do ambiente
    config.update({
        'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', config['telegram_token']),
        'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', config['telegram_chat_id']),
        'email_usuario': os.getenv('EMAIL_USER', config['email_usuario']),
        'email_senha': os.getenv('EMAIL_PASSWORD', config['email_senha']),
        'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL', config['discord_webhook_url']),
        'webhook_url': os.getenv('WEBHOOK_URL', config['webhook_url'])
    })
    
    return GerenciadorAlertas(config)


if __name__ == "__main__":
    # Teste do sistema de alertas
    import asyncio
    
    async def testar_alertas():
        """Teste básico do sistema de alertas"""
        print("🧪 Testando Sistema de Alertas...")
        
        # Configuração de teste (sem credenciais reais)
        config = {
            'ativo': True,
            'canais_ativos': ['telegram'],  # Apenas para demonstração
            'telegram_token': 'test_token',
            'telegram_chat_id': 'test_chat_id'
        }
        
        gerenciador = criar_gerenciador_alertas(config)
        
        # Testar diferentes tipos de alerta
        await gerenciador.alerta_info("Sistema Iniciado", "O bot de trading foi iniciado com sucesso")
        await gerenciador.alerta_trade("Nova Ordem", "Ordem de compra executada", {"simbolo": "BTC/USDT", "preco": 50000})
        await gerenciador.alerta_warning("Alerta de Risco", "Drawdown aproximando do limite")
        
        # Obter estatísticas
        stats = await gerenciador.obter_estatisticas()
        print(f"📊 Estatísticas: {stats['total_alertas_enviados']} alertas enviados")
        
        print("✅ Teste concluído!")
    
    # Executar teste
    asyncio.run(testar_alertas())
