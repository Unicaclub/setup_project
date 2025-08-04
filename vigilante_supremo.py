"""
Script de automação resiliente para renomeação, refatoração e validação do projeto CryptoLogger Pro.
Executa em loop até conseguir renomear o diretório data-ingestion para data_ingestion, refatora imports, executa testes e gera log detalhado.
"""
import os
import sys
import time
import shutil
import re
from pathlib import Path
import subprocess

# Configurações
OLD_DIR = Path('cryptologger-pro/services/data-ingestion')
NEW_DIR = Path('cryptologger-pro/services/data_ingestion')
LOG_PATH = Path('cryptologger-pro/logs/refatoracao_imports.log')
README_PATH = Path('cryptologger-pro/README.md')
RENAME_OK = False
MAX_RETRIES = 1000
SLEEP_SECONDS = 5

BACKUP_SUFFIX = '.bak_vigilante'

# Função para log seguro
def log(msg):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)

def backup_file(path):
    backup = Path(str(path) + BACKUP_SUFFIX)
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
        log(f"Backup criado: {backup}")

def restore_backup(path):
    backup = Path(str(path) + BACKUP_SUFFIX)
    if backup.exists():
        shutil.copy2(backup, path)
        log(f"Restaurado backup: {backup}")

def try_rename():
    try:
        if not OLD_DIR.exists():
            log(f"Diretório antigo não existe mais: {OLD_DIR}")
            return True
        if NEW_DIR.exists():
            log(f"Diretório destino já existe: {NEW_DIR}")
            return False
        shutil.move(str(OLD_DIR), str(NEW_DIR))
        log(f"Renomeado: {OLD_DIR} -> {NEW_DIR}")
        return True
    except Exception as e:
        log(f"Falha ao renomear: {e}")
        return False

def refatora_imports():
    log("Iniciando refatoração de imports...")
    alterados = []
    for root, _, files in os.walk('cryptologger-pro'):
        for file in files:
            if file.endswith('.py'):
                path = Path(root) / file
                backup_file(path)
                with open(path, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                novo = re.sub(r'(from|import)\s+data-ingestion([\.|\s])', r'\1 data_ingestion\2', conteudo)
                novo = re.sub(r'(from|import)\s+data_ingestion([\.|\s])', r'\1 data_ingestion\2', novo) # idempotente
                if conteudo != novo:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(novo)
                    alterados.append(str(path))
    log(f"Arquivos alterados: {alterados}")
    return alterados

def atualiza_readme():
    if README_PATH.exists():
        backup_file(README_PATH)
        with open(README_PATH, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        novo = conteudo.replace('data-ingestion', 'data_ingestion')
        if conteudo != novo:
            with open(README_PATH, 'w', encoding='utf-8') as f:
                f.write(novo)
            log(f"README.md atualizado.")

def executa_testes():
    log("Executando testes automatizados...")
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', 'cryptologger-pro/tests'], capture_output=True, text=True, timeout=600)
        log("Saída dos testes:\n" + result.stdout)
        if result.returncode == 0:
            log("Todos os testes passaram com sucesso!")
            return True
        else:
            log("Falhas nos testes!\n" + result.stderr)
            return False
    except Exception as e:
        log(f"Erro ao executar testes: {e}")
        return False

def main():
    tentativas = 0
    while tentativas < MAX_RETRIES:
        tentativas += 1
        log(f"Tentativa {tentativas}: Verificando possibilidade de renomeação...")
        if try_rename():
            log("Renomeação concluída!")
            break
        time.sleep(SLEEP_SECONDS)
    else:
        log("ERRO FATAL: Não foi possível renomear após várias tentativas.")
        sys.exit(1)

    alterados = refatora_imports()
    atualiza_readme()
    sucesso = executa_testes()
    if not sucesso:
        log("Rollback automático dos arquivos alterados...")
        for path in alterados:
            restore_backup(path)
        restore_backup(README_PATH)
        log("Rollback concluído. Corrija os erros e execute novamente.")
        sys.exit(2)
    log("✅ Renomeação, refatoração e testes concluídos com sucesso!")

if __name__ == "__main__":
    main()
