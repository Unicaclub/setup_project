#!/usr/bin/env python3
"""
CryptoTradeBotGlobal - Sistema Principal de Execução
Bot de Trading de Criptomoedas com Gerenciamento de Risco Avançado
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path
from typing import Optional

# Adicionar o diretório src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from src.utils.logger import configurar_logger
from src.core.bot_trading import BotTrading
from config import CarregarConfiguracoes, validar_configuracoes


class GerenciadorSistema:
    """Gerenciador principal do sistema de trading"""
    
    def __init__(self):
        self.bot_trading: Optional[BotTrading] = None
        self.logger = logging.getLogger(__name__)
        self.executando = False
        
    async def inicializar_sistema(self) -> bool:
        """
        Inicializa todos os componentes do sistema
        
        Returns:
            True se inicializado com sucesso
        """
        try:
            self.logger.info("🚀 Iniciando CryptoTradeBotGlobal...")
            
            # Carregar configurações
            self.logger.info("📋 Carregando configurações...")
            configuracoes = CarregarConfiguracoes()
            
            # Validar configurações
            if not validar_configuracoes(configuracoes):
                self.logger.error("❌ Configurações inválidas!")
                return False
            
            self.logger.info("✅ Configurações carregadas com sucesso")
            
            # Inicializar bot de trading
            self.logger.info("🤖 Inicializando bot de trading...")
            self.bot_trading = BotTrading(configuracoes)
            
            # Conectar aos exchanges
            sucesso_conexao = await self.bot_trading.conectar_exchanges()
            if not sucesso_conexao:
                self.logger.error("❌ Falha ao conectar com exchanges!")
                return False
            
            self.logger.info("🏦 Conectado aos exchanges com sucesso")
            
            # Inicializar sistema de gerenciamento de risco
            await self.bot_trading.inicializar_gerenciamento_risco()
            self.logger.info("🛡️ Sistema de gerenciamento de risco ativo")
            
            self.executando = True
            self.logger.info("✅ Sistema inicializado com sucesso!")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante inicialização: {str(e)}")
            return False
    
    async def executar_loop_principal(self):
        """Loop principal de execução do bot"""
        try:
            self.logger.info("🔄 Iniciando loop principal de trading...")
            
            while self.executando:
                try:
                    # Executar ciclo de trading
                    await self.bot_trading.executar_ciclo_trading()
                    
                    # Aguardar próximo ciclo (30 segundos)
                    await asyncio.sleep(30)
                    
                except KeyboardInterrupt:
                    self.logger.info("⏹️ Interrupção solicitada pelo usuário")
                    break
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro no loop principal: {str(e)}")
                    # Aguardar antes de tentar novamente
                    await asyncio.sleep(60)
                    
        except Exception as e:
            self.logger.error(f"❌ Erro crítico no loop principal: {str(e)}")
        finally:
            await self.finalizar_sistema()
    
    async def finalizar_sistema(self):
        """Finaliza o sistema de forma segura"""
        try:
            self.logger.info("🔄 Finalizando sistema...")
            self.executando = False
            
            if self.bot_trading:
                await self.bot_trading.finalizar()
                
            self.logger.info("✅ Sistema finalizado com sucesso")
            
        except Exception as e:
            self.logger.error(f"❌ Erro durante finalização: {str(e)}")
    
    def configurar_manipuladores_sinal(self):
        """Configura manipuladores para sinais do sistema"""
        def manipular_sinal(signum, frame):
            self.logger.info(f"📡 Sinal recebido: {signum}")
            self.executando = False
        
        signal.signal(signal.SIGINT, manipular_sinal)
        signal.signal(signal.SIGTERM, manipular_sinal)


async def main():
    """Função principal do sistema"""
    # Configurar logging
    configurar_logger()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 60)
        logger.info("🤖 CRYPTOTRADEBOTGLOBAL - SISTEMA DE TRADING")
        logger.info("=" * 60)
        
        # Criar gerenciador do sistema
        gerenciador = GerenciadorSistema()
        gerenciador.configurar_manipuladores_sinal()
        
        # Inicializar sistema
        if not await gerenciador.inicializar_sistema():
            logger.error("❌ Falha na inicialização do sistema")
            sys.exit(1)
        
        # Executar loop principal
        await gerenciador.executar_loop_principal()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Sistema interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro crítico: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("👋 Encerrando CryptoTradeBotGlobal")


if __name__ == "__main__":
    try:
        # Verificar versão do Python
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ é necessário para executar este sistema")
            sys.exit(1)
        
        # Executar sistema
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n⏹️ Sistema interrompido")
    except Exception as e:
        print(f"❌ Erro fatal: {str(e)}")
        sys.exit(1)
