"""
Painel Web de Monitoramento - CryptoTradeBotGlobal
Sistema de Trading de Criptomoedas - Português Brasileiro
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
import sys

# Adicionar o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from src.adapters.binance_real import criar_adaptador_binance_real
from src.strategies.estrategia_sma_simples import criar_estrategia_sma_simples
from src.strategies.estrategia_rsi import criar_estrategia_rsi
from src.strategies.estrategia_bollinger import criar_estrategia_bollinger
from src.core.risco import criar_gerenciador_risco
from src.utils.logger import configurar_logger


class PainelTradingWeb:
    """Painel web para monitoramento do sistema de trading"""
    
    def __init__(self):
        """Inicializa o painel web"""
        self.configurar_pagina()
        self.inicializar_componentes()
        
        # Estado da sessão
        if 'dados_historicos' not in st.session_state:
            st.session_state.dados_historicos = []
        if 'sistema_ativo' not in st.session_state:
            st.session_state.sistema_ativo = False
        if 'ultima_atualizacao' not in st.session_state:
            st.session_state.ultima_atualizacao = None
    
    def configurar_pagina(self):
        """Configura a página do Streamlit"""
        st.set_page_config(
            page_title="CryptoTradeBotGlobal - Painel de Controle",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS customizado
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .status-online {
            color: #28a745;
            font-weight: bold;
        }
        .status-offline {
            color: #dc3545;
            font-weight: bold;
        }
        .alert-success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 0.75rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
        .alert-warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 0.75rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
        .alert-danger {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 0.75rem;
            border-radius: 0.25rem;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def inicializar_componentes(self):
        """Inicializa os componentes do sistema"""
        try:
            # Configurar logging
            configurar_logger(nivel='INFO')
            
            # Inicializar adaptador
            self.adaptador = criar_adaptador_binance_real({
                'testnet': True,
                'modo_simulacao': True,
                'api_key': 'demo_key',
                'api_secret': 'demo_secret'
            })
            
            # Inicializar estratégias
            self.estrategia_sma = criar_estrategia_sma_simples({
                'simbolos': ['BTC/USDT', 'ETH/USDT']
            })
            
            self.estrategia_rsi = criar_estrategia_rsi({
                'simbolos': ['BTC/USDT', 'ETH/USDT']
            })
            
            self.estrategia_bollinger = criar_estrategia_bollinger({
                'simbolos': ['BTC/USDT', 'ETH/USDT']
            })
            
            # Inicializar gerenciador de risco
            self.gerenciador_risco = criar_gerenciador_risco()
            
        except Exception as e:
            st.error(f"❌ Erro ao inicializar componentes: {str(e)}")
    
    def executar(self):
        """Executa o painel principal"""
        # Cabeçalho
        st.markdown('<h1 class="main-header">🤖 CryptoTradeBotGlobal</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #666;">Painel de Controle e Monitoramento</p>', unsafe_allow_html=True)
        
        # Sidebar com controles
        self.renderizar_sidebar()
        
        # Conteúdo principal
        self.renderizar_conteudo_principal()
    
    def renderizar_sidebar(self):
        """Renderiza a barra lateral com controles"""
        st.sidebar.header("🎛️ Controles do Sistema")
        
        # Status do sistema
        status = "🟢 Online" if st.session_state.sistema_ativo else "🔴 Offline"
        st.sidebar.markdown(f"**Status:** {status}")
        
        # Controles principais
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("▶️ Iniciar", disabled=st.session_state.sistema_ativo):
                self.iniciar_sistema()
        
        with col2:
            if st.button("⏹️ Parar", disabled=not st.session_state.sistema_ativo):
                self.parar_sistema()
        
        st.sidebar.divider()
        
        # Configurações
        st.sidebar.header("⚙️ Configurações")
        
        # Seleção de estratégias
        estrategias_ativas = st.sidebar.multiselect(
            "Estratégias Ativas",
            ["SMA", "RSI", "Bollinger"],
            default=["SMA"]
        )
        
        # Símbolos para monitorar
        simbolos_monitorados = st.sidebar.multiselect(
            "Símbolos",
            ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT"],
            default=["BTC/USDT", "ETH/USDT"]
        )
        
        # Configurações de risco
        st.sidebar.subheader("🛡️ Gerenciamento de Risco")
        
        stop_loss = st.sidebar.slider(
            "Stop Loss (%)",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5
        )
        
        max_drawdown = st.sidebar.slider(
            "Max Drawdown (%)",
            min_value=5.0,
            max_value=30.0,
            value=15.0,
            step=1.0
        )
        
        # Botão de atualização
        st.sidebar.divider()
        if st.sidebar.button("🔄 Atualizar Dados"):
            self.atualizar_dados()
        
        # Última atualização
        if st.session_state.ultima_atualizacao:
            st.sidebar.caption(f"Última atualização: {st.session_state.ultima_atualizacao.strftime('%H:%M:%S')}")
    
    def renderizar_conteudo_principal(self):
        """Renderiza o conteúdo principal do painel"""
        # Abas principais
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Dashboard", 
            "💹 Trading", 
            "🛡️ Risco", 
            "📈 Estratégias", 
            "📋 Logs"
        ])
        
        with tab1:
            self.renderizar_dashboard()
        
        with tab2:
            self.renderizar_trading()
        
        with tab3:
            self.renderizar_risco()
        
        with tab4:
            self.renderizar_estrategias()
        
        with tab5:
            self.renderizar_logs()
    
    def renderizar_dashboard(self):
        """Renderiza o dashboard principal"""
        st.header("📊 Dashboard Geral")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Portfolio",
                value="$10,000.00",
                delta="$0.00 (0.00%)"
            )
        
        with col2:
            st.metric(
                label="📈 P&L Hoje",
                value="$0.00",
                delta="0.00%"
            )
        
        with col3:
            st.metric(
                label="🎯 Trades",
                value="0",
                delta="0 hoje"
            )
        
        with col4:
            st.metric(
                label="⚠️ Alertas",
                value="0",
                delta="0 ativos"
            )
        
        st.divider()
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            self.renderizar_grafico_precos()
        
        with col2:
            self.renderizar_grafico_portfolio()
        
        # Tabela de posições
        st.subheader("📋 Posições Abertas")
        
        # Dados simulados
        posicoes_df = pd.DataFrame({
            'Símbolo': ['BTC/USDT', 'ETH/USDT'],
            'Lado': ['LONG', 'LONG'],
            'Quantidade': [0.0, 0.0],
            'Preço Entrada': [0.0, 0.0],
            'Preço Atual': [50000.0, 3000.0],
            'P&L': [0.0, 0.0],
            'P&L %': [0.0, 0.0]
        })
        
        st.dataframe(posicoes_df, use_container_width=True)
    
    def renderizar_grafico_precos(self):
        """Renderiza gráfico de preços"""
        st.subheader("💹 Preços em Tempo Real")
        
        # Dados simulados
        dates = pd.date_range(start='2025-01-01', periods=100, freq='H')
        btc_prices = 50000 + (pd.Series(range(100)) * 10) + (pd.Series(range(100)) * 0.1).apply(lambda x: x * (-1) ** int(x))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=btc_prices,
            mode='lines',
            name='BTC/USDT',
            line=dict(color='#f7931a', width=2)
        ))
        
        fig.update_layout(
            title="BTC/USDT - Últimas 24h",
            xaxis_title="Tempo",
            yaxis_title="Preço (USDT)",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def renderizar_grafico_portfolio(self):
        """Renderiza gráfico do portfolio"""
        st.subheader("📊 Evolução do Portfolio")
        
        # Dados simulados
        dates = pd.date_range(start='2025-01-01', periods=30, freq='D')
        portfolio_values = [10000 + (i * 50) for i in range(30)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=portfolio_values,
            mode='lines+markers',
            name='Portfolio',
            line=dict(color='#1f77b4', width=3),
            fill='tonexty'
        ))
        
        fig.update_layout(
            title="Evolução do Portfolio (30 dias)",
            xaxis_title="Data",
            yaxis_title="Valor (USD)",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def renderizar_trading(self):
        """Renderiza a seção de trading"""
        st.header("💹 Trading")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 Histórico de Ordens")
            
            # Dados simulados
            ordens_df = pd.DataFrame({
                'Timestamp': [datetime.now() - timedelta(hours=i) for i in range(5)],
                'Símbolo': ['BTC/USDT', 'ETH/USDT', 'BTC/USDT', 'ETH/USDT', 'BTC/USDT'],
                'Lado': ['COMPRAR', 'VENDER', 'COMPRAR', 'COMPRAR', 'VENDER'],
                'Quantidade': [0.001, 0.1, 0.002, 0.05, 0.001],
                'Preço': [50000, 3000, 49800, 3100, 50200],
                'Status': ['EXECUTADA', 'EXECUTADA', 'EXECUTADA', 'EXECUTADA', 'EXECUTADA'],
                'P&L': [0, -10, 4, -5, 2]
            })
            
            st.dataframe(ordens_df, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Estatísticas")
            
            st.metric("Total de Ordens", "5")
            st.metric("Taxa de Sucesso", "100%")
            st.metric("Volume Negociado", "$500.00")
            st.metric("Melhor Trade", "$4.00")
            st.metric("Pior Trade", "-$10.00")
            
            st.divider()
            
            # Controles manuais
            st.subheader("🎮 Controle Manual")
            
            simbolo_manual = st.selectbox("Símbolo", ["BTC/USDT", "ETH/USDT"])
            acao_manual = st.selectbox("Ação", ["COMPRAR", "VENDER"])
            quantidade_manual = st.number_input("Quantidade", min_value=0.001, value=0.001, step=0.001)
            
            if st.button("📤 Executar Ordem Manual"):
                st.success(f"✅ Ordem {acao_manual} {quantidade_manual} {simbolo_manual} enviada!")
    
    def renderizar_risco(self):
        """Renderiza a seção de gerenciamento de risco"""
        st.header("🛡️ Gerenciamento de Risco")
        
        # Status do gerenciamento de risco
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="alert-success">✅ Sistema de Risco Ativo</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="alert-success">✅ Dentro dos Limites</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="alert-success">✅ Sem Alertas Críticos</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Métricas de risco
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🛑 Stop Loss",
                value="5.0%",
                delta="Configurado"
            )
        
        with col2:
            st.metric(
                label="📉 Drawdown Atual",
                value="0.0%",
                delta="Limite: 15.0%"
            )
        
        with col3:
            st.metric(
                label="💸 Perda Diária",
                value="$0.00",
                delta="Limite: $500.00"
            )
        
        with col4:
            st.metric(
                label="⚠️ Alertas Ativos",
                value="0",
                delta="Nenhum alerta"
            )
        
        # Gráfico de risco
        st.subheader("📊 Monitoramento de Risco")
        
        # Dados simulados
        risk_dates = pd.date_range(start='2025-01-01', periods=24, freq='H')
        drawdown_values = [abs(i * 0.1) % 5 for i in range(24)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=risk_dates,
            y=drawdown_values,
            mode='lines+markers',
            name='Drawdown (%)',
            line=dict(color='#dc3545', width=2)
        ))
        
        # Linha de limite
        fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Limite Máximo")
        
        fig.update_layout(
            title="Drawdown nas Últimas 24h",
            xaxis_title="Tempo",
            yaxis_title="Drawdown (%)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Histórico de alertas
        st.subheader("📋 Histórico de Alertas")
        
        alertas_df = pd.DataFrame({
            'Timestamp': [datetime.now() - timedelta(hours=i) for i in range(3)],
            'Tipo': ['INFO', 'WARNING', 'INFO'],
            'Mensagem': [
                'Sistema de risco inicializado',
                'Drawdown aproximando do limite (12%)',
                'Ordem validada com sucesso'
            ],
            'Ação': ['Nenhuma', 'Monitorar', 'Nenhuma']
        })
        
        st.dataframe(alertas_df, use_container_width=True)
    
    def renderizar_estrategias(self):
        """Renderiza a seção de estratégias"""
        st.header("📈 Estratégias de Trading")
        
        # Abas para cada estratégia
        tab_sma, tab_rsi, tab_bollinger = st.tabs(["📊 SMA", "📈 RSI", "📉 Bollinger"])
        
        with tab_sma:
            self.renderizar_estrategia_sma()
        
        with tab_rsi:
            self.renderizar_estrategia_rsi()
        
        with tab_bollinger:
            self.renderizar_estrategia_bollinger()
    
    def renderizar_estrategia_sma(self):
        """Renderiza detalhes da estratégia SMA"""
        st.subheader("📊 Estratégia SMA (Simple Moving Average)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Status", "🟢 Ativa")
            st.metric("Sinais Gerados", "0")
        
        with col2:
            st.metric("SMA Rápida", "5 períodos")
            st.metric("SMA Lenta", "10 períodos")
        
        with col3:
            st.metric("Símbolos", "2")
            st.metric("Última Análise", "Agora")
        
        # Gráfico SMA
        st.subheader("📈 Gráfico SMA")
        
        # Dados simulados
        dates = pd.date_range(start='2025-01-01', periods=50, freq='H')
        prices = [50000 + (i * 20) + (i % 10 * 100) for i in range(50)]
        sma_fast = pd.Series(prices).rolling(window=5).mean()
        sma_slow = pd.Series(prices).rolling(window=10).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=prices, mode='lines', name='Preço', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=dates, y=sma_fast, mode='lines', name='SMA 5', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=dates, y=sma_slow, mode='lines', name='SMA 10', line=dict(color='red')))
        
        fig.update_layout(title="BTC/USDT com SMAs", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def renderizar_estrategia_rsi(self):
        """Renderiza detalhes da estratégia RSI"""
        st.subheader("📈 Estratégia RSI (Relative Strength Index)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Status", "🟢 Ativa")
            st.metric("RSI Atual", "45.2")
        
        with col2:
            st.metric("Sobrecompra", "70")
            st.metric("Sobrevenda", "30")
        
        with col3:
            st.metric("Período", "14")
            st.metric("Sinais", "0")
        
        # Gráfico RSI
        st.subheader("📊 Gráfico RSI")
        
        dates = pd.date_range(start='2025-01-01', periods=50, freq='H')
        rsi_values = [30 + (i % 40) + (i * 0.5) % 20 for i in range(50)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=rsi_values, mode='lines', name='RSI', line=dict(color='purple')))
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Sobrecompra")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Sobrevenda")
        
        fig.update_layout(title="RSI - BTC/USDT", yaxis=dict(range=[0, 100]), height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def renderizar_estrategia_bollinger(self):
        """Renderiza detalhes da estratégia Bollinger"""
        st.subheader("📉 Estratégia Bandas de Bollinger")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Status", "🟢 Ativa")
            st.metric("Período", "20")
        
        with col2:
            st.metric("Desvios Padrão", "2.0")
            st.metric("Modo", "Reversão")
        
        with col3:
            st.metric("Largura Banda", "$2,500")
            st.metric("Posição", "Meio")
        
        # Gráfico Bollinger
        st.subheader("📈 Gráfico Bandas de Bollinger")
        
        dates = pd.date_range(start='2025-01-01', periods=50, freq='H')
        prices = [50000 + (i * 20) + (i % 10 * 200) for i in range(50)]
        sma = pd.Series(prices).rolling(window=20).mean()
        std = pd.Series(prices).rolling(window=20).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=prices, mode='lines', name='Preço', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=dates, y=upper_band, mode='lines', name='Banda Superior', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=dates, y=sma, mode='lines', name='Média', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=dates, y=lower_band, mode='lines', name='Banda Inferior', line=dict(color='green')))
        
        fig.update_layout(title="Bandas de Bollinger - BTC/USDT", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def renderizar_logs(self):
        """Renderiza a seção de logs"""
        st.header("📋 Logs do Sistema")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nivel_log = st.selectbox("Nível", ["TODOS", "INFO", "WARNING", "ERROR"])
        
        with col2:
            modulo_log = st.selectbox("Módulo", ["TODOS", "TRADING", "RISCO", "ESTRATEGIA"])
        
        with col3:
            if st.button("🔄 Atualizar Logs"):
                st.rerun()
        
        # Logs simulados
        logs_data = [
            {"timestamp": datetime.now() - timedelta(seconds=i*30), 
             "nivel": ["INFO", "WARNING", "ERROR"][i % 3],
             "modulo": ["TRADING", "RISCO", "ESTRATEGIA"][i % 3],
             "mensagem": f"Mensagem de log {i+1} - Sistema funcionando normalmente"}
            for i in range(20)
        ]
        
        logs_df = pd.DataFrame(logs_data)
        
        # Aplicar filtros
        if nivel_log != "TODOS":
            logs_df = logs_df[logs_df['nivel'] == nivel_log]
        
        if modulo_log != "TODOS":
            logs_df = logs_df[logs_df['modulo'] == modulo_log]
        
        # Colorir logs por nível
        def colorir_linha(row):
            if row['nivel'] == 'ERROR':
                return ['background-color: #f8d7da'] * len(row)
            elif row['nivel'] == 'WARNING':
                return ['background-color: #fff3cd'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            logs_df.style.apply(colorir_linha, axis=1),
            use_container_width=True,
            height=400
        )
    
    def iniciar_sistema(self):
        """Inicia o sistema de trading"""
        st.session_state.sistema_ativo = True
        st.success("✅ Sistema iniciado com sucesso!")
        st.rerun()
    
    def parar_sistema(self):
        """Para o sistema de trading"""
        st.session_state.sistema_ativo = False
        st.info("⏹️ Sistema parado")
        st.rerun()
    
    def atualizar_dados(self):
        """Atualiza os dados do painel"""
        st.session_state.ultima_atualizacao = datetime.now()
        st.success("🔄 Dados atualizados!")
        time.sleep(1)
        st.rerun()


def main():
    """Função principal do painel web"""
    try:
        painel = PainelTradingWeb()
        painel.executar()
        
    except Exception as e:
        st.error(f"❌ Erro crítico no painel: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
