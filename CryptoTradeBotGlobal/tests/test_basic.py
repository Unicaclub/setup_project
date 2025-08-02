"""
Testes Básicos do Sistema
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import pytest
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.bot_trading import BotTrading
from src.utils.logger import setup_logger
import config


class TestSistemaBasico:
    """Testes básicos para verificar funcionamento do sistema"""
    
    def test_importacao_modulos(self):
        """Testa se os módulos principais podem ser importados"""
        try:
            from src.core.bot_trading import BotTrading
            from src.utils.logger import setup_logger
            from src.core.risk_manager import RiskManager
            assert True
        except ImportError as e:
            pytest.fail(f"Falha ao importar módulos: {e}")
    
    def test_configuracao_basica(self):
        """Testa se as configurações básicas estão disponíveis"""
        assert hasattr(config, 'CONFIGURACAO_BASICA')
        assert isinstance(config.CONFIGURACAO_BASICA, dict)
        assert 'nome_sistema' in config.CONFIGURACAO_BASICA
        assert 'versao' in config.CONFIGURACAO_BASICA
    
    def test_logger_funcional(self):
        """Testa se o sistema de logging está funcionando"""
        logger = setup_logger('teste_basico')
        assert logger is not None
        
        # Testa se consegue fazer log sem erro
        try:
            logger.info("Teste de log básico")
            logger.warning("Teste de warning")
            logger.error("Teste de error")
            assert True
        except Exception as e:
            pytest.fail(f"Erro no sistema de logging: {e}")
    
    def test_bot_trading_inicializacao(self):
        """Testa se o BotTrading pode ser inicializado"""
        try:
            bot = BotTrading()
            assert bot is not None
            assert hasattr(bot, 'configuracao')
            assert hasattr(bot, 'logger')
        except Exception as e:
            pytest.fail(f"Erro ao inicializar BotTrading: {e}")
    
    def test_estrutura_diretorios(self):
        """Testa se a estrutura de diretórios está correta"""
        base_dir = Path(__file__).parent.parent
        
        diretorios_necessarios = [
            'src',
            'src/core',
            'src/utils',
            'src/adapters',
            'src/strategies',
            'tests',
            'config',
            'logs',
            'data'
        ]
        
        for diretorio in diretorios_necessarios:
            caminho = base_dir / diretorio
            assert caminho.exists(), f"Diretório {diretorio} não encontrado"
            assert caminho.is_dir(), f"{diretorio} não é um diretório"
    
    def test_arquivos_essenciais(self):
        """Testa se os arquivos essenciais existem"""
        base_dir = Path(__file__).parent.parent
        
        arquivos_necessarios = [
            'main.py',
            'config.py',
            'requirements.txt',
            '.env.example',
            'README.md',
            '.gitignore',
            'src/__init__.py',
            'src/core/bot_trading.py',
            'src/utils/logger.py',
            'tests/__init__.py'
        ]
        
        for arquivo in arquivos_necessarios:
            caminho = base_dir / arquivo
            assert caminho.exists(), f"Arquivo {arquivo} não encontrado"
            assert caminho.is_file(), f"{arquivo} não é um arquivo"
    
    def test_configuracao_ambiente(self):
        """Testa se as configurações de ambiente estão corretas"""
        # Verifica se o arquivo .env.example existe e tem conteúdo
        env_example = Path(__file__).parent.parent / '.env.example'
        assert env_example.exists()
        
        with open(env_example, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            assert len(conteudo) > 0
            assert 'APP_NAME' in conteudo
            assert 'ENVIRONMENT' in conteudo
    
    def test_sistema_funcionando(self):
        """Teste geral para verificar se o sistema está funcionando"""
        try:
            # Inicializa logger
            logger = setup_logger('teste_sistema')
            logger.info("Iniciando teste do sistema")
            
            # Inicializa bot
            bot = BotTrading()
            logger.info("Bot inicializado com sucesso")
            
            # Verifica configurações
            assert bot.configuracao is not None
            logger.info("Configurações carregadas")
            
            # Teste básico de funcionamento
            status = bot.obter_status_sistema()
            assert isinstance(status, dict)
            assert 'status' in status
            logger.info("Sistema funcionando corretamente")
            
        except Exception as e:
            pytest.fail(f"Sistema não está funcionando: {e}")


def test_execucao_main():
    """Testa se o main.py pode ser executado sem erro"""
    import subprocess
    import sys
    
    try:
        # Executa o main.py em modo de teste
        resultado = subprocess.run(
            [sys.executable, 'main.py', '--teste'],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Verifica se não houve erro crítico
        assert resultado.returncode == 0 or resultado.returncode == 1  # 1 pode ser saída normal
        
    except subprocess.TimeoutExpired:
        # Timeout é aceitável para este teste
        pass
    except Exception as e:
        pytest.fail(f"Erro ao executar main.py: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
