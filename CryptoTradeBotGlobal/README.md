# CryptoTradeBotGlobal – Fase 5 SUPREMA
## 🚀 Deploy Local/Dev/Prod
```sh
docker-compose --profile dev up -d
# ou
docker-compose --profile prod up -d
```
- API: http://localhost:8000
- Painel Admin: http://localhost:8080
- Streamlit: http://localhost:8501
- PostgreSQL: localhost:5432
- Redis: localhost:6379
## 🏢 Multi-Tenant SaaS
- Cada tenant tem seus próprios usuários, planos, assinaturas, dados segregados.
- JWT obrigatório nas rotas privadas.
- SSO JWT no painel Streamlit (exemplo em `src/api/streamlit_sso.py`).
## 🔑 Usuário/Admin/Tenant/Assinatura
- Seeds: admin@root.com (senha: admin123), Demo Tenant, Plano Demo.
- CRUD: /usuarios, /planos, /assinaturas, /tenants.
- Login: /login (JWT), Google OAuth2 (exemplo/documentação).
## 💸 Stripe Billing (Sandbox)
- Stripe Checkout integrado (sandbox).
- Webhooks: pagamento, renovação, cancelamento.
- Teste: use cartões de teste Stripe.
## 🛡️ Painel Admin & Streamlit
- Painel admin FastAPI-admin (ou próprio).
- Streamlit: cada tenant só vê seus dados/ordens.
- Exemplo de uso JWT no painel.
## 🧪 Testes & Seeds
- Testes automáticos: pytest, FastAPI TestClient, Stripe mock.
- Scripts seed: `python src/api/seeds.py`.
## 📚 Documentação
- Endpoints: Swagger em `/docs`.
- Exemplos de uso API JSON no README.
- Roadmap Fase 6: ML, backtest, auto-otimização.
## 🔗 Exemplos de API
```json
POST /login
{
  "username": "admin@root.com",
  "password": "admin123"
}

GET /usuarios (JWT)
Authorization: Bearer <token>

POST /planos (JWT)
{
  "nome": "Pro",
  "preco": 99.9,
  "descricao": "Plano Pro"
}
```

## 🛣️ Roadmap Fase 6
- Estratégias ML, backtest multi-tenant, auto-otimização, relatórios avançados.
# 🤖 CryptoTradeBotGlobal

**Sistema Completo de Trading de Criptomoedas em Português Brasileiro**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Licença: MIT](https://img.shields.io/badge/Licença-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Código: Black](https://img.shields.io/badge/código-black-000000.svg)](https://github.com/psf/black)

Sistema de trading de criptomoedas pronto para produção com gerenciamento avançado de risco, arquitetura empresarial e suporte a múltiplos exchanges.

## 🎯 Características Principais

### 🏗️ **Arquitetura Empresarial**
- **Design Modular**: Separação clara de responsabilidades com padrão adapter
- **Async/Await**: Operações assíncronas de alta performance
- **Orientado a Eventos**: Bus de eventos em tempo real para comunicação do sistema
- **Pronto para Microserviços**: Suporte a deployment com Docker e Kubernetes
- **Escalável**: Escalabilidade horizontal com clustering Redis

### 📈 **Estratégias de Trading Avançadas**
- **Análise Técnica**: RSI, MACD, Bandas de Bollinger, Médias Móveis
- **Reversão à Média**: Arbitragem estatística e pair trading
- **Seguimento de Tendência**: Estratégias baseadas em momentum
- **Trading de Rompimento**: Rompimentos de níveis de suporte/resistência
- **Arbitragem**: Exploração de diferenças de preço entre exchanges
- **Machine Learning**: Modelos ensemble LSTM, Random Forest, XGBoost

### 🛡️ **Gerenciamento de Risco Empresarial**
- **Controles de Risco de Portfólio**: Limites de drawdown, dimensionamento de posição
- **Monitoramento em Tempo Real**: Cálculos de VaR, CVaR, índice Sharpe
- **Circuit Breakers**: Parada automática de trading em perdas excessivas
- **Procedimentos de Emergência**: Mecanismos fail-safe e protocolos de recuperação

### 🔗 **Suporte Multi-Exchange**
- **Binance**: Trading spot e futuros
- **Coinbase Pro**: Interface de trading profissional
- **Kraken**: Acesso ao mercado europeu
- **Extensível**: Fácil adição de novos exchanges

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.8 ou superior
- PostgreSQL 12+ (para produção)
- Redis 6+ (para cache e pub/sub)
- Docker & Docker Compose (opcional)

### Instalação

1. **Clonar o Repositório**
```bash
git clone https://github.com/Unicaclub/setup_project.git
cd setup_project/CryptoTradeBotGlobal
```

2. **Criar Ambiente Virtual**
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. **Instalar Dependências**
```bash
pip install -r requirements.txt
```

4. **Configurar Ambiente**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Executar o Sistema**
```bash
python main.py
```

### Deployment com Docker

```bash
# Construir e executar com Docker Compose
docker-compose up -d

# Escalar serviços
docker-compose up -d --scale trading-engine=3
```

## 📊 Configuração

### Variáveis de Ambiente

O sistema usa variáveis de ambiente para configuração. Copie `.env.example` para `.env` e configure:

```bash
# Configuração de Trading
TRADING_MODE=simulacao  # simulacao, real, backtest
TRADING_BASE_CURRENCY=USDT
TRADING_MAX_POSITION_SIZE=1000.0

# Chaves de API dos Exchanges (mantenha seguro!)
BINANCE_API_KEY=sua_chave_api_aqui
BINANCE_SECRET_KEY=sua_chave_secreta_aqui

# Gerenciamento de Risco
TRADING_MAX_DAILY_LOSS=500.0
TRADING_MAX_DRAWDOWN=0.15
```

### Configuração de Estratégias

As estratégias são configuradas em `config/strategies.yaml`:

```yaml
estrategias:
  seguimento_tendencia:
    ativo: true
    parametros:
      periodo_ma_rapida: 12
      periodo_ma_lenta: 26
      stop_loss_pct: 0.03
    gerenciamento_risco:
      tamanho_max_posicao: 1000.0
      risco_por_trade: 0.02
```

### Gerenciamento de Risco

Os parâmetros de risco são definidos em `config/risk_management.yaml`:

```yaml
risco_portfolio:
  risco_max_portfolio: 0.10
  perda_max_diaria: 0.05
  drawdown_maximo: 0.20
```

## 🏗️ Arquitetura

### Componentes do Sistema

## 🚨 Exemplos de Alertas Enviados

Exemplo de alerta multi-canal:

```python
from src.utils import alertas
alertas.enviar_alerta("Alerta de risco: Stop-loss atingido!", tipo="RISK", canais=["telegram", "email", "discord"], urgente=True)
```

Exemplo de alerta crítico:

```python
alertas.enviar_alerta("Erro crítico: Falha na conexão com Binance!", tipo="CRITICAL", canais=["email"], urgente=True)
```

Estatísticas dos alertas:

```python
stats = alertas.estatisticas_alertas()
print(stats)
```

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Motor de      │    │   Gerenciador   │    │   Gerenciador   │
│   Trading       │◄──►│   Estratégias   │◄──►│   de Risco      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Adaptadores   │    │   Gerenciador   │    │   Gerenciador   │
│   Exchange      │    │   de Dados      │    │   Portfolio     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bus de        │◄──►│   Gerenciador   │◄──►│   Monitor de    │
│   Eventos       │    │   de Estado     │    │   Saúde         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Estrutura de Diretórios

```
CryptoTradeBotGlobal/
├── src/
│   ├── core/                 # Componentes principais do sistema
│   │   ├── bot_trading.py    # Bot principal de trading
│   │   ├── event_bus.py      # Comunicação orientada a eventos
│   │   ├── state_manager.py  # Gerenciamento de estado
│   │   └── health_monitor.py # Monitoramento de saúde
│   ├── adapters/             # Adaptadores de exchange
│   │   └── exchanges/        # Implementações específicas
│   ├── strategies/           # Estratégias de trading
│   │   ├── technical/        # Estratégias de análise técnica
│   │   ├── arbitrage/        # Estratégias de arbitragem
│   │   └── ml_strategies/    # Estratégias de machine learning
│   └── utils/                # Funções utilitárias
├── config/                   # Arquivos de configuração
│   ├── settings.py          # Configuração principal
│   ├── exchanges.yaml       # Configurações de exchanges
│   ├── strategies.yaml      # Parâmetros de estratégias
│   └── risk_management.yaml # Regras de gerenciamento de risco
├── tests/                   # Suíte de testes
├── docs/                    # Documentação
├── data/                    # Armazenamento de dados
└── logs/                    # Arquivos de log
```

## 📈 Estratégias de Trading

### Estratégias de Análise Técnica

#### Seguimento de Tendência
- **Cruzamento de Médias Móveis**: EMA 12/26 com confirmação de sinal
- **Estratégia MACD**: Cruzamentos de linha MACD e linha de sinal
- **Trading de Momentum**: Indicadores RSI e momentum de preço

#### Reversão à Média
- **Bandas de Bollinger**: Reversão de preço à média com bandas de volatilidade
- **RSI Sobrevendido/Sobrecomprado**: Sinais contrários em níveis extremos
- **Arbitragem Estatística**: Pair trading com análise de correlação

### Estratégias de Machine Learning

#### Redes Neurais LSTM
- **Predição de Preços**: Previsão de séries temporais com LSTM
- **Engenharia de Features**: Indicadores técnicos e dados de mercado
- **Métodos Ensemble**: Combinação de múltiplos modelos

## 🛡️ Gerenciamento de Risco

### Controles de Risco de Portfólio

### Integração com `binance_real`

O adaptador `binance_real` implementa integração real com a API oficial da Binance (spot), suportando tanto a biblioteca oficial `binance.client` quanto `ccxt` para máxima flexibilidade. Inclui:
- CRUD de ordens reais e simuladas
- Logs detalhados e tratamento de edge cases
- Criptografia de credenciais
- Métodos assíncronos para operações de alta performance
- Testes integrados e rotina de simulação

Exemplo de uso:
```python
from src.adapters.binance_real import criar_adaptador_binance_real
adaptador = criar_adaptador_binance_real({'modo_simulacao': True})
# adaptador.conectar(), adaptador.executar_ordem(...)
```

### Gestão de Risco Empresarial

O módulo `src/core/gestor_risco.py` implementa:
- Stop-loss por posição (% do saldo inicial)
- Drawdown diário com bloqueio automático de ordens
- Reset automático por janela de tempo
- Integração com alertas e logs

Exemplo de integração:
```python
from src.core.gestor_risco import GestorRisco
gestor = GestorRisco(limite_stop=0.05, limite_drawdown=0.10)
gestor.registrar_saldo(10000)
gestor.registrar_trade('BTCUSDT', -600)
if not gestor.pode_operar():
    print('Operação bloqueada por risco!')
```

- **Dimensionamento de Posição**: Critério de Kelly, percentual fixo, ajustado por volatilidade
- **Diversificação**: Limites máximos de correlação e concentração
- **Proteção de Drawdown**: Redução dinâmica de posição em perdas
- **Gerenciamento de Stop Loss**: Stops móveis e tomada de lucro

### Monitoramento em Tempo Real

- **Value at Risk (VaR)**: Medição de risco com 95% de confiança
- **VaR Condicional**: Cálculo de shortfall esperado
- **Índice Sharpe**: Monitoramento de retorno ajustado ao risco
- **Drawdown Máximo**: Rastreamento de perda pico-vale

## 🔧 Desenvolvimento

### Configurando Ambiente de Desenvolvimento

1. **Instalar Dependências de Desenvolvimento**
```bash
pip install pytest pytest-asyncio
```

2. **Executar Testes**
```bash
pytest tests/ -v
```

3. **Executar Testes Básicos**
```bash
python tests/test_basico.py
```

### Adicionando Novos Exchanges

1. Criar adaptador de exchange em `src/adapters/exchanges/`
2. Implementar interface `BaseExchange`
3. Adicionar configuração em `config/exchanges.yaml`
4. Adicionar testes em `tests/adapters/exchanges/`

### Adicionando Novas Estratégias

1. Criar classe de estratégia herdando de `BaseStrategy`
2. Implementar métodos obrigatórios: `analyze()`, `generate_signal()`, `calculate_risk()`
3. Adicionar configuração em `config/strategies.yaml`
4. Adicionar testes abrangentes

## 📊 Monitoramento e Observabilidade

### Métricas e Monitoramento

- **Métricas Prometheus**: Métricas de sistema e trading
- **Dashboards Grafana**: Visualização em tempo real
- **Health Checks**: Monitoramento de endpoints
- **Rastreamento de Performance**: Métricas de latência e throughput

### Logging

- **Logging Estruturado**: Logs formatados em JSON com contexto
- **Níveis de Log**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Trilha de Auditoria**: Log completo de decisões de trading
- **Rotação de Logs**: Gerenciamento automático de arquivos de log

## 🚀 Deployment

### Deployment de Produção

### Comandos Docker Compose

```bash
# Subir todos os serviços (produção)
docker-compose --profile prod up -d

# Subir ambiente de desenvolvimento
docker-compose --profile dev up -d

# Parar todos os serviços
docker-compose down
```

### Healthchecks e Monitoramento

Todos os serviços possuem healthcheck configurado. Métricas Prometheus e dashboards Grafana disponíveis em:
- http://localhost:9090 (Prometheus)
- http://localhost:3000 (Grafana)

#### Deployment Docker
```bash
# Construir imagem de produção
docker build -t cryptobot:latest .

# Executar com configuração de produção
docker run -d --name cryptobot \
  --env-file .env.production \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  cryptobot:latest
```

### Configurações Específicas por Ambiente

#### Desenvolvimento
- Paper trading habilitado
- Logging de debug
- Banco de dados local
- Tamanhos de posição reduzidos

#### Produção
- Trading ao vivo habilitado
- Performance otimizada
- Configuração de alta disponibilidade
- Monitoramento abrangente

## 🔐 Segurança

### Gerenciamento de Chaves de API

- **Criptografia**: Criptografia AES-256 para chaves armazenadas
- **Variáveis de Ambiente**: Gerenciamento seguro de configuração
- **Rotação de Chaves**: Rotação automática de chaves de API
- **Controle de Acesso**: Acesso baseado em funções para operações sensíveis

### Auditoria e Conformidade

- **Log de Transações**: Trilha de auditoria completa
- **Retenção de Dados**: Políticas de retenção configuráveis
- **Relatórios de Conformidade**: Geração de relatórios regulatórios
- **Log de Acesso**: Monitoramento de atividade do usuário

## 📚 Documentação

## 🗺️ Roadmap Fase 5 (SaaS)

- [ ] Multiusuário e autenticação OAuth2
- [ ] Painel SaaS com billing e planos
- [ ] Deploy automatizado (CI/CD)
- [ ] API pública para integrações externas
- [ ] Estratégias customizáveis via painel web
- [ ] Monitoramento multi-conta e multi-exchange
- [ ] Suporte a backtests massivos e relatórios avançados

### Documentação da API

- **Documentação FastAPI**: Documentação de API auto-gerada
- **Especificação OpenAPI**: Especificação de API legível por máquina

### Guias do Usuário

- **Primeiros Passos**: Guia de configuração rápida
- **Configuração**: Opções de configuração detalhadas
- **Desenvolvimento de Estratégias**: Criação de estratégias personalizadas
- **Solução de Problemas**: Problemas comuns e soluções

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, veja nosso [Guia de Contribuição](CONTRIBUTING.md) para detalhes.

### Fluxo de Desenvolvimento

1. Faça fork do repositório
2. Crie uma branch de feature
3. Faça suas alterações
4. Adicione testes
5. Execute a suíte de testes
6. Submeta um pull request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ⚠️ Aviso Legal

**IMPORTANTE**: Este software é para fins educacionais e de pesquisa. O trading de criptomoedas envolve risco substancial de perda. Performance passada não garante resultados futuros. Sempre:

- Comece com paper trading
- Nunca invista mais do que pode perder
- Entenda os riscos envolvidos
- Cumpra as regulamentações locais
- Procure aconselhamento financeiro profissional

## 🆘 Suporte

### Obtendo Ajuda

- **Documentação**: Consulte nossa documentação abrangente
- **Issues**: Reporte bugs no GitHub Issues
- **Discussões**: Participe das GitHub Discussions

### Suporte Profissional

Para suporte empresarial, desenvolvimento personalizado ou serviços de consultoria, entre em contato:
- Email: suporte@cryptotradebotglobal.com
- Website: https://cryptotradebotglobal.com

## 🙏 Agradecimentos

- **Biblioteca CCXT**: Integração com exchanges de criptomoedas
- **FastAPI**: Framework web moderno
- **PostgreSQL**: Sistema de banco de dados confiável
- **Redis**: Cache de alta performance
- **Docker**: Plataforma de containerização

---

**Construído com ❤️ pela Equipe CryptoTradeBotGlobal**

*Tornando o trading de criptomoedas acessível, seguro e lucrativo para todos.*

## 🚀 Como Executar

### Execução Básica

```bash
# Executar o sistema principal
python main.py

# Executar testes
python tests/test_basico.py

# Executar com pytest
pytest tests/ -v
```

### Configuração Rápida

1. **Configure as chaves de API no arquivo `.env`**:
```bash
# Exemplo de configuração mínima
BINANCE_API_KEY=sua_chave_binance
BINANCE_API_SECRET=sua_chave_secreta_binance
BINANCE_TESTNET=true
```

2. **Execute o sistema**:
```bash
python main.py
```

3. **Monitore os logs**:
```bash
tail -f logs/trading.log
```

### Recursos Implementados

✅ **Sistema de Configuração Completo**
✅ **Gerenciamento de Risco Avançado**
✅ **Adaptadores de Exchange (Simulados)**
✅ **Sistema de Logging Profissional**
✅ **Bot de Trading Principal**
✅ **Suíte de Testes Abrangente**
✅ **Documentação Completa**

**SISTEMA INICIALIZADO COM SUCESSO - PROJETO FUNCIONAL**
