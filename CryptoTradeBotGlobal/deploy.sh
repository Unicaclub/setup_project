#!/bin/bash
# Script de deploy automatizado para CryptoTradeBotGlobal
# Uso: bash deploy.sh

set -e

# 1. Entre no diretório do projeto
cd /root/CryptoTradeBotGlobal

echo "[1/7] Atualizando código do repositório..."
git pull origin main

echo "[2/7] Adicionando alterações locais..."
git add .

echo "[3/7] Commitando alterações..."
git commit -m "Deploy: atualização total, pronto para produção" || echo "Nenhuma alteração para commitar."

echo "[4/7] Enviando para o repositório remoto..."
git push origin main

echo "[5/7] Build e deploy com Docker Compose..."
docker compose up --build -d

echo "[6/7] Rodando testes automatizados..."
pytest --maxfail=1 --disable-warnings -v || { echo "[ERRO] Testes falharam!"; exit 1; }

echo "[7/7] Deploy finalizado com sucesso!"
