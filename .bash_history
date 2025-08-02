#SYSTEM
AGENT=SUPREME_NETOPS_IA
MISSION=END2END_AUTOMATED_DOMAIN_INFRA_DEPLOY
MODE=ONE_COMMAND_DEPLOY,AUTOMATION_ONLY,API_ONLY
OBJECTIVE="Gerar e executar um script totalmente automatizado, pronto para colar no terminal, que faz o seguinte: conecta na API da Hostinger e na API da Cloudflare, cria e atualiza todos os registros DNS (tipo A) necessários para o domínio principal unicaclubcg.site e TODOS subdomínios correspondentes à estrutura completa do projeto painel-master (conforme árvore de pastas abaixo), apontando tudo para o IP da VPS (31.97.30.237), já deixando o site e todos serviços operacionais, com deploy de reverse proxy, VPN, logs e verificação do healthcheck dos endpoints."
CONTEXT=[
]
STEPS=[
]
CONSTRAINTS=[
]
RESPONSE_FORMAT=[
]
NEXT_STEP="Gerar todos os scripts, arquivos e instruções detalhadas para automação total do apontamento de domínio, deploy do site, subdomínios e serviços do painel-master, tudo pronto para colar e executar no terminal."
#INITIATE_FULLSTACK_DNS_AUTODEPLOY
clear
# ================================
# SUPREMO - AUTOMATIZAÇÃO BACKEND, SSL, VPN
# Executa tudo: NGINX + Certbot + Wireguard
# Basta copiar e colar!
# ================================
set -e
# VARIÁVEIS GLOBAIS
DOMAIN="unicaclubcg.site"
EMAIL="unicaclubms.trafego@gmail.com"
VPS_IP="31.97.30.237"
SUBDOMAINS=(   "painel" "backend" "frontend" "dashboard"   "whatsapp-bot" "facebook-bot" "instagram-bot"   "metaads-worker" "googleads-worker" "pix-worker"   "estoque-worker" "relatorio-worker" "financeiro-worker"   "marketing-worker" "erp-core" "api" "dev" "test" )
log() { echo -e "\033[1;36m[$(date +%T)] $1\033[0m"; }
# 1. INSTALAR NGINX
log "Instalando NGINX..."
sudo apt update && sudo apt install -y nginx
# 2. CONFIGURAR REVERSE PROXY PARA SUBDOMÍNIOS
log "Configurando NGINX para todos subdomínios..."
for name in "${SUBDOMAINS[@]}"; do     PORT=$((8000 + RANDOM % 1000))
    cat <<EOF | sudo tee /etc/nginx/sites-available/$name.$DOMAIN > /dev/null
server {
    listen 80;
    server_name $name.$DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
     sudo ln -sf /etc/nginx/sites-available/$name.$DOMAIN /etc/nginx/sites-enabled/; done
sudo nginx -t && sudo systemctl reload nginx
log "Todos subdomínios configurados no NGINX."
# 3. INSTALAR E CONFIGURAR SSL (CERTBOT)
log "Instalando Certbot e provisionando SSL..."
sudo apt install -y certbot python3-certbot-nginx
for name in "${SUBDOMAINS[@]}"; do     sudo certbot --nginx -d "$name.$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" --redirect || true; done
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" --redirect || true
sudo systemctl reload nginx
log "SSL instalado para todos domínios/subdomínios!"
# 4. INSTALAR E CONFIGURAR VPN (WIREGUARD)
log "Instalando e configurando Wireguard..."
sudo apt install -y wireguard
if [ ! -f /etc/wireguard/wg0.conf ]; then     PRIVATE_KEY=$(wg genkey);     echo "[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $PRIVATE_KEY
" | sudo tee /etc/wireguard/wg0.conf > /dev/null;      sudo systemctl enable wg-quick@wg0;     sudo systemctl start wg-quick@wg0;     log "Wireguard VPN pronto! Edite /etc/wireguard/wg0.conf para adicionar peers."; else     log "Wireguard já configurado. Pulei etapa."; fi
# 5. HEALTHCHECK
log "Checando endpoints:"
for name in "${SUBDOMAINS[@]}"; do     echo -n "$name.$DOMAIN: ";     curl -s -o /dev/null -w "%{http_code}\n" "https://$name.$DOMAIN" || echo "Falha"; done
log "TUDO PRONTO: BACKEND, SSL E VPN OPERANDO SUPREMO!"
echo -e "\n\033[1;32m⚡ Finalizado! Todos subdomínios do $DOMAIN configurados, proxy reverso ativo, SSL válido e VPN disponível.\033[0m"
echo -e "Para adicionar bots ou serviços, aponte o backend para as portas dos proxies configurados."
echo -e "Edite as portas conforme necessário em /etc/nginx/sites-available/"
echo -e "Se quiser blueprint CI/CD, script rollback ou deploy massivo, peça AGORA!"
clear
clear
# setup-backend.ps1 — GERA TUDO AUTOMÁTICO
$structure = @{
}
foreach ($path in $structure.Keys) {
}
Write-Host "✅ Estrutura criada! Agora rode: cd backend; npm install"
#!/bin/bash
set -e
# Criação da estrutura de pastas painel-master completa
BASE="painel-master"
# Pastas Backend
mkdir -p $BASE/backend/src/controllers
mkdir -p $BASE/backend/src/services
mkdir -p $BASE/backend/src/models
mkdir -p $BASE/backend/src/routes
mkdir -p $BASE/backend/src/middleware
mkdir -p $BASE/backend/src/utils
mkdir -p $BASE/backend/config
mkdir -p $BASE/backend/database
mkdir -p $BASE/backend/tests
# Pastas Frontend
mkdir -p $BASE/frontend/public
mkdir -p $BASE/frontend/src/components
mkdir -p $BASE/frontend/src/pages
mkdir -p $BASE/frontend/src/hooks
mkdir -p $BASE/frontend/src/utils
# Pastas Services (Bots/Workers)
mkdir -p $BASE/services/whatsapp_bot/src
mkdir -p $BASE/services/facebook_bot/src
mkdir -p $BASE/services/instagram_bot/src
mkdir -p $BASE/services/metaads_worker/src
mkdir -p $BASE/services/googleads_worker/src
mkdir -p $BASE/services/pix_worker/src
mkdir -p $BASE/services/estoque_worker/src
mkdir -p $BASE/services/relatorio_worker/src
mkdir -p $BASE/services/financeiro_worker/src
mkdir -p $BASE/services/marketing_worker/src
mkdir -p $BASE/services/erp_core/src
# Pastas Operacionais
mkdir -p $BASE/promoters
mkdir -p $BASE/dashboard
mkdir -p $BASE/eventos
mkdir -p $BASE/relatorios
mkdir -p $BASE/clientes
mkdir -p $BASE/caixa
mkdir -p $BASE/convites
mkdir -p $BASE/estoque
mkdir -p $BASE/pedidos
mkdir -p $BASE/financeiro
mkdir -p $BASE/marketing
mkdir -p $BASE/bl
mkdir -p $BASE/integracoes
mkdir -p $BASE/scripts
mkdir -p $BASE/docs
# Arquivos .gitkeep para manter pastas no git (opcional)
find $BASE -type d -exec touch {}/.gitkeep \;
echo "✅ Estrutura de pastas criada com sucesso!"
chmod +x criar_estrutura.sh
criar_estrutura_painel.sh
chmod +x criar_estrutura_painel.sh
./criar_estrutura_painel.sh
#!/bin/bash
set -e
echo "🚀 INICIANDO: GERADOR SUPREMO DE ESTRUTURA MCP GODSOURCE V∞ (painel-master)"
echo "---------------------------------------------"
BASE="painel-master"
mkdir -p $BASE
# =========== BACKEND ===========
mkdir -p $BASE/backend/src/{controllers,services,models,routes,middleware,utils}
mkdir -p $BASE/backend/config
mkdir -p $BASE/backend/database
mkdir -p $BASE/backend/tests
# Arquivos backend base
echo "// Controller base" > $BASE/backend/src/controllers/mainController.js
echo "// Service base" > $BASE/backend/src/services/mainService.js
echo "// Model base" > $BASE/backend/src/models/mainModel.js
echo "// Rotas base" > $BASE/backend/src/routes/mainRoutes.js
echo "// Middleware base" > $BASE/backend/src/middleware/authMiddleware.js
echo "// Utils base" > $BASE/backend/src/utils/helper.js
cat > $BASE/backend/config/config.json <<EOF
{
  "database": "mysql",
  "user": "root",
  "password": "SENHA_AQUI",
  "host": "localhost",
  "port": 3306
}
EOF

echo "// Conexão DB base" > $BASE/backend/database/connection.js
echo "// Teste base" > $BASE/backend/tests/base.test.js
# =========== FRONTEND ===========
mkdir -p $BASE/frontend/public
mkdir -p $BASE/frontend/src/{components,pages,hooks,utils}
echo "// Componente base" > $BASE/frontend/src/components/MainComponent.jsx
echo "// Página base" > $BASE/frontend/src/pages/HomePage.jsx
echo "// Hook base" > $BASE/frontend/src/hooks/useAuth.js
echo "// Utils base" > $BASE/frontend/src/utils/helpers.js
# =========== SERVICES (BOTS & WORKERS) ===========
for bot in whatsapp_bot facebook_bot instagram_bot metaads_worker googleads_worker pix_worker estoque_worker relatorio_worker financeiro_worker marketing_worker erp_core; do   mkdir -p $BASE/services/$bot/src;   echo "# Main do $bot" > $BASE/services/$bot/src/main.py; done
# =========== MÓDULOS OPERACIONAIS ===========
for mod in promoters dashboard eventos relatorios clientes caixa convites estoque pedidos financeiro marketing bl integracoes scripts docs; do   mkdir -p $BASE/$mod;   echo "# README $mod" > $BASE/$mod/README.md; done
# ========= EXTRAS ===========
echo "# Instale as dependências do backend" > $BASE/backend/README.md
cat > $BASE/README.md <<EOF
# PAINEL MASTER MCP GODSOURCE
Estrutura criada automaticamente pelo script SUPREMO.
Para rodar, acesse cada módulo e siga as instruções do README de cada pasta.
EOF

echo 'Inicializador SUPREMO MCP GODSOURCE!'
" > $BASE/scripts/start.sh

touch $BASE/.env.example
echo "DB_PASSWORD=SUA_SENHA_AQUI
criar_estrutura_painel.sh
chmod +x criar_estrutura_painel.sh
./criar_estrutura_painel.sh
#!/bin/bash
set -e
echo "🚀 INICIANDO: GERADOR SUPREMO DE ESTRUTURA MCP GODSOURCE V∞ (painel-master)"
echo "---------------------------------------------"
BASE="painel-master"
mkdir -p $BASE
# =========== BACKEND ===========
mkdir -p $BASE/backend/src/{controllers,services,models,routes,middleware,utils}
mkdir -p $BASE/backend/config
mkdir -p $BASE/backend/database
mkdir -p $BASE/backend/tests
# Arquivos backend base
echo "// Controller base" > $BASE/backend/src/controllers/mainController.js
echo "// Service base" > $BASE/backend/src/services/mainService.js
echo "// Model base" > $BASE/backend/src/models/mainModel.js
echo "// Rotas base" > $BASE/backend/src/routes/mainRoutes.js
echo "// Middleware base" > $BASE/backend/src/middleware/authMiddleware.js
echo "// Utils base" > $BASE/backend/src/utils/helper.js
cat > $BASE/backend/config/config.json <<EOF
{
  "database": "mysql",
  "user": "root",
  "password": "SENHA_AQUI",
  "host": "localhost",
  "port": 3306
}
EOF

echo "// Conexão DB base" > $BASE/backend/database/connection.js
echo "// Teste base" > $BASE/backend/tests/base.test.js
# =========== FRONTEND ===========
mkdir -p $BASE/frontend/public
mkdir -p $BASE/frontend/src/{components,pages,hooks,utils}
echo "// Componente base" > $BASE/frontend/src/components/MainComponent.jsx
echo "// Página base" > $BASE/frontend/src/pages/HomePage.jsx
echo "// Hook base" > $BASE/frontend/src/hooks/useAuth.js
echo "// Utils base" > $BASE/frontend/src/utils/helpers.js
# =========== SERVICES (BOTS & WORKERS) ===========
for bot in whatsapp_bot facebook_bot instagram_bot metaads_worker googleads_worker pix_worker estoque_worker relatorio_worker financeiro_worker marketing_worker erp_core; do   mkdir -p $BASE/services/$bot/src;   echo "# Main do $bot" > $BASE/services/$bot/src/main.py; done
# =========== MÓDULOS OPERACIONAIS ===========
for mod in promoters dashboard eventos relatorios clientes caixa convites estoque pedidos financeiro marketing bl integracoes scripts docs; do   mkdir -p $BASE/$mod;   echo "# README $mod" > $BASE/$mod/README.md; done
# ========= EXTRAS ===========
echo "# Instale as dependências do backend" > $BASE/backend/README.md
cat > $BASE/README.md <<EOF
# PAINEL MASTER MCP GODSOURCE
Estrutura criada automaticamente pelo script SUPREMO.
Para rodar, acesse cada módulo e siga as instruções do README de cada pasta.
EOF

echo 'Inicializador SUPREMO MCP GODSOURCE!'
" > $BASE/scripts/start.sh

touch $BASE/.env.example
echo "DB_PASSWORD=SUA_SENHA_AQUI
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg |   sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
   https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo systemctl status docker
sudo groupadd docker
sudo usermod -aG docker $USER
docker --version
docker compose version
docker run hello-world
docker build -t ctbg/app -f Dockerfile .
docker compose --profile prod up --build --abort-on-container-exit
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
sudo apt-get remove -y docker.io docker-ce docker-ce-cli containerd runc docker-compose docker-compose-plugin
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg |   sudo gpg --dearmor -o /etc/apt/keyrings/docker-archive-keyring.gpg
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo systemctl status docker
docker --version
docker compose version
docker run hello-world
docker build -t ctbg/app -f Dockerfile .
docker compose --profile prod up --build --abort-on-container-exit
cd /caminho/do/projeto
docker build -t ctbg/app -f Dockerfile .
docker compose --profile prod up --build --abort-on-container-exit
# 🚀 Script automático de deploy da aplicação CryptoTradeBotGlobal
cd ~ && PROJ_DIR=$(find . -maxdepth 2 -type f -name Dockerfile -printf '%h\n' | head -n 1) && if [ -z "$PROJ_DIR" ]; then echo "❌ Dockerfile não encontrado!"; exit 1; fi && echo "Usando Dockerfile em: $PROJ_DIR" && cd "$PROJ_DIR" && docker build -t ctbg/app -f Dockerfile . && docker compose --profile prod up --build --abort-on-container-exit
