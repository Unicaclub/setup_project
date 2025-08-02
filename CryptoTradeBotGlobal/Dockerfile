FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
# Opcional: Remover arquivos de dev/testes para imagem final enxuta

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y curl && \
    addgroup --system appgroup && adduser --system appuser --ingroup appgroup && \
    rm -rf /var/lib/apt/lists/*
USER appuser
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 8000 8501
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail http://localhost:8000/health || curl --fail http://localhost:8501/_stcore/health || exit 1
# Por padrão, inicia a API FastAPI. Para rodar o painel, altere o CMD abaixo.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"]
# Para rodar o painel Streamlit, use:
# CMD ["sh", "-c", "streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0"]
# Dockerfile para CryptoTradeBotGlobal
# Sistema de Trading de Criptomoedas - Português Brasileiro

FROM python:3.11-slim

# Metadados
LABEL maintainer="CryptoTradeBotGlobal Team"
LABEL description="Sistema de Trading de Criptomoedas em Português Brasileiro"
LABEL version="1.0.0"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root para segurança
RUN groupadd -r cryptobot && useradd -r -g cryptobot cryptobot

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY requirements.txt .
COPY setup.py .

# Instala dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Cria diretórios necessários
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R cryptobot:cryptobot /app

# Copia código fonte
COPY --chown=cryptobot:cryptobot . .

# Muda para usuário não-root
USER cryptobot

# Expõe porta da API
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando padrão
CMD ["python", "main.py"]
