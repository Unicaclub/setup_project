"""
import streamlit as st
import plotly.graph_objs as go
import requests
import os
import jwt

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="CryptoTradeBotGlobal Dashboard", layout="wide")

# Integração SSO JWT
jwt_token = st.session_state.get("JWT_TOKEN") or st.text_input("Cole seu JWT aqui:", type="password")
headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}

st.title("CryptoTradeBotGlobal – Dashboard Multi-Tenant")

abas = st.tabs(["Trading", "Risco", "Logs", "Dashboard"])

with abas[0]:
    st.header("Trading")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Bot"):
            if jwt_token:
                r = requests.post(f"{API_URL}/bot/start", headers=headers)
                st.write(r.json())
            else:
                st.warning("JWT obrigatório!")
    with col2:
        if st.button("Stop Bot"):
            if jwt_token:
                r = requests.post(f"{API_URL}/bot/stop", headers=headers)
                st.write(r.json())
            else:
                st.warning("JWT obrigatório!")
    # Gráfico de ordens
    if jwt_token:
        r = requests.get(f"{API_URL}/ordens", headers=headers)
        if r.ok:
            ordens = r.json()
            if ordens:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=[o['timestamp'] for o in ordens], y=[o['preco'] for o in ordens], mode='lines+markers', name='Preço'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem ordens para exibir.")
        else:
            st.info("Sem ordens para exibir.")

with abas[1]:
    st.header("Gestão de Risco")
    if jwt_token:
        r = requests.get(f"{API_URL}/risco", headers=headers)
        if r.ok:
            risco = r.json()
            if risco:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=list(risco.keys()), y=list(risco.values())))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de risco.")
        else:
            st.info("Sem dados de risco.")
    else:
        st.warning("JWT obrigatório!")

with abas[2]:
    st.header("Logs do Sistema")
    if jwt_token:
        r = requests.get(f"{API_URL}/logs", headers=headers)
        if r.ok:
            logs = r.json()
            if logs:
                st.code("\n".join(logs[-100:]), language="text")
            else:
                st.info("Sem logs.")
        else:
            st.info("Sem logs.")
    else:
        st.warning("JWT obrigatório!")

with abas[3]:
    st.header("Dashboard de Performance")
    if jwt_token:
        r = requests.get(f"{API_URL}/performance", headers=headers)
        if r.ok:
            perf = r.json()
            if perf and 'datas' in perf and 'pnl' in perf:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=perf['datas'], y=perf['pnl'], mode='lines+markers', name='PnL'))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados de performance.")
        else:
            st.info("Sem dados de performance.")
    else:
        st.warning("JWT obrigatório!")
    st.session_state.bot_running = False
if 'dados_historicos' not in st.session_state:
    st.session_state.dados_historicos = []
if 'alertas_manager' not in st.session_state:
    st.session_state.alertas_manager = None

# Logger
logger = obter_logger(__name__)

class DashboardManager:
    """Gerenciador do dashboard Streamlit"""
    
    def __init__(self):
        self.config = obter_configuracao()
        self.dados_simulados = self._gerar_dados_simulados()
        
    def _gerar_dados_simulados(self) -> Dict[str, Any]:
        """Gera dados simulados para demonstração"""
        import random
        import numpy as np
        
        # Gerar dados de preços simulados
        base_price = 50000
        timestamps = []
        prices = []
        volumes = []
        
        for i in range(100):
            timestamp = datetime.now() - timedelta(minutes=100-i)
            price = base_price + random.uniform(-1000, 1000) + np.sin(i/10) * 500
            volume = random.uniform(1000, 5000)
            
            timestamps.append(timestamp)
            prices.append(price)
            volumes.append(volume)
        
        return {
            'timestamps': timestamps,
            'prices': prices,
            'volumes': volumes,
            'portfolio_value': 10000.0,
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'drawdown': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_volume': 0.0
        }
    
    def criar_grafico_precos(self) -> go.Figure:
        """Cria gráfico de preços em tempo real"""
        fig = go.Figure()
        
        # Linha de preços
        fig.add_trace(go.Scatter(
            x=self.dados_simulados['timestamps'],
            y=self.dados_simulados['prices'],
            mode='lines',
            name='BTC/USDT',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # Configurações do layout
        fig.update_layout(
            title='Preço BTC/USDT em Tempo Real',
            xaxis_title='Tempo',
            yaxis_title='Preço (USDT)',
            height=400,
            showlegend=True,
            hovermode='x unified'
        )
        
        return fig
    
    def criar_grafico_volume(self) -> go.Figure:
        """Cria gráfico de volume"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=self.dados_simulados['timestamps'][-20:],  # Últimos 20 pontos
            y=self.dados_simulados['volumes'][-20:],
            name='Volume',
            marker_color='rgba(31, 119, 180, 0.6)'
        ))
        
        fig.update_layout(
            title='Volume de Negociação',
            xaxis_title='Tempo',
            yaxis_title='Volume',
            height=300,
            showlegend=False
        )
        
        return fig
    
    def criar_grafico_pnl(self) -> go.Figure:
        """Cria gráfico de P&L"""
        # Simular dados de P&L
        pnl_data = [0]
        for i in range(1, len(self.dados_simulados['timestamps'])):
            change = random.uniform(-50, 50)
            pnl_data.append(pnl_data[-1] + change)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=self.dados_simulados['timestamps'],
            y=pnl_data,
            mode='lines',
            name='P&L',
            line=dict(color='green' if pnl_data[-1] > 0 else 'red', width=2),
            fill='tonexty' if pnl_data[-1] > 0 else None
        ))
        
        fig.update_layout(
            title='Profit & Loss (P&L)',
            xaxis_title='Tempo',
            yaxis_title='P&L (USDT)',
            height=300,
            showlegend=False
        )
        
        return fig

# Instância do gerenciador
dashboard = DashboardManager()

def main():
    """Função principal do dashboard"""
    
    # Cabeçalho
    st.markdown('<h1 class="main-header">🤖 CryptoTradeBotGlobal Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar - Controles
    with st.sidebar:
        st.header("🎛️ Controles do Sistema")
        
        # Status do bot
        if st.session_state.bot_running:
            st.markdown('<p class="status-running">🟢 Bot Ativo</p>', unsafe_allow_html=True)
            if st.button("⏹️ Parar Bot", type="secondary"):
                st.session_state.bot_running = False
                st.success("Bot parado com sucesso!")
                st.rerun()
        else:
            st.markdown('<p class="status-stopped">🔴 Bot Parado</p>', unsafe_allow_html=True)
            if st.button("▶️ Iniciar Bot", type="primary"):
                st.session_state.bot_running = True
                st.success("Bot iniciado com sucesso!")
                st.rerun()
        
        st.divider()
        
        # Configurações rápidas
        st.subheader("⚙️ Configurações Rápidas")
        
        modo_trading = st.selectbox(
            "Modo de Trading",
            ["Simulação", "Testnet", "Produção"],
            index=0
        )
        
        simbolos_selecionados = st.multiselect(
            "Símbolos Ativos",
            ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT"],
            default=["BTC/USDT"]
        )
        
        st.divider()
        
        # Estratégias ativas
        st.subheader("📊 Estratégias")
        
        estrategia_sma = st.checkbox("SMA (Média Móvel)", value=True)
        estrategia_rsi = st.checkbox("RSI", value=False)
        estrategia_bollinger = st.checkbox("Bandas de Bollinger", value=False)
        
        st.divider()
        
        # Alertas
        st.subheader("📢 Alertas")
        
        alertas_telegram = st.checkbox("Telegram", value=False)
        alertas_email = st.checkbox("Email", value=False)
        alertas_discord = st.checkbox("Discord", value=False)
    
    # Abas principais
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "💹 Trading", 
        "🛡️ Risco", 
        "📈 Estratégias", 
        "📋 Logs"
    ])
    
    with tab1:
        dashboard_tab()
    
    with tab2:
        trading_tab()
    
    with tab3:
        risco_tab()
    
    with tab4:
        estrategias_tab()
    
    with tab5:
        logs_tab()

def dashboard_tab():
    """Aba principal do dashboard"""
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Portfolio",
            value=f"${dashboard.dados_simulados['portfolio_value']:,.2f}",
            delta=f"{dashboard.dados_simulados['pnl_percent']:+.2f}%"
        )
    
    with col2:
        st.metric(
            label="📈 P&L",
            value=f"${dashboard.dados_simulados['pnl']:+,.2f}",
            delta=f"{dashboard.dados_simulados['pnl']:+.2f}"
        )
    
    with col3:
        st.metric(
            label="📉 Drawdown",
            value=f"{dashboard.dados_simulados['drawdown']:.2f}%",
            delta=f"{dashboard.dados_simulados['drawdown']:+.2f}%"
        )
    
    with col4:
        st.metric(
            label="🔄 Trades",
            value=dashboard.dados_simulados['total_trades'],
            delta=f"+{dashboard.dados_simulados['total_trades']}"
        )
    
    st.divider()
    
    # Gráficos principais
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gráfico de preços
        fig_precos = dashboard.criar_grafico_precos()
        st.plotly_chart(fig_precos, use_container_width=True)
    
    with col2:
        # Estatísticas rápidas
        st.subheader("📊 Estatísticas")
        
        st.markdown(f"""
        **Trades Vencedores:** {dashboard.dados_simulados['winning_trades']}  
        **Trades Perdedores:** {dashboard.dados_simulados['losing_trades']}  
        **Volume Total:** ${dashboard.dados_simulados['total_volume']:,.2f}  
        **Taxa de Acerto:** {0 if dashboard.dados_simulados['total_trades'] == 0 else (dashboard.dados_simulados['winning_trades'] / dashboard.dados_simulados['total_trades'] * 100):.1f}%
        """)
        
        # Gráfico de P&L
        fig_pnl = dashboard.criar_grafico_pnl()
        st.plotly_chart(fig_pnl, use_container_width=True)
    
    # Gráfico de volume
    st.subheader("📊 Volume de Negociação")
    fig_volume = dashboard.criar_grafico_volume()
    st.plotly_chart(fig_volume, use_container_width=True)

def trading_tab():
    """Aba de trading"""
    
    st.header("💹 Painel de Trading")
    
    # Controles manuais
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Ordem Manual")
        
        with st.form("ordem_manual"):
            simbolo = st.selectbox("Símbolo", ["BTC/USDT", "ETH/USDT", "BNB/USDT"])
            tipo_ordem = st.selectbox("Tipo", ["COMPRAR", "VENDER"])
            quantidade = st.number_input("Quantidade", min_value=0.001, value=0.01, step=0.001)
            preco = st.number_input("Preço (deixe 0 para mercado)", min_value=0.0, value=0.0)
            
            submitted = st.form_submit_button("🚀 Executar Ordem")
            
            if submitted:
                st.success(f"Ordem {tipo_ordem} de {quantidade} {simbolo} enviada!")
    
    with col2:
        st.subheader("📋 Posições Abertas")
        
        # Simular posições
        posicoes_df = pd.DataFrame({
            'Símbolo': ['BTC/USDT'],
            'Lado': ['LONG'],
            'Quantidade': [0.1],
            'Preço Entrada': [49500.0],
            'Preço Atual': [50000.0],
            'P&L': [50.0],
            'P&L %': [1.01]
        })
        
        if not posicoes_df.empty:
            st.dataframe(posicoes_df, use_container_width=True)
        else:
            st.info("Nenhuma posição aberta")
    
    st.divider()
    
    # Histórico de ordens
    st.subheader("📜 Histórico de Ordens")
    
    # Simular histórico
    historico_df = pd.DataFrame({
        'Timestamp': [datetime.now() - timedelta(minutes=i*5) for i in range(5)],
        'Símbolo': ['BTC/USDT'] * 5,
        'Tipo': ['COMPRAR', 'VENDER', 'COMPRAR', 'VENDER', 'COMPRAR'],
        'Quantidade': [0.01, 0.01, 0.015, 0.01, 0.02],
        'Preço': [49800, 50200, 49500, 50100, 49900],
        'Status': ['EXECUTADA'] * 5,
        'P&L': [0, 4.0, 0, 6.0, 0]
    })
    
    st.dataframe(historico_df, use_container_width=True)

def risco_tab():
    """Aba de gerenciamento de risco"""
    
    st.header("🛡️ Gerenciamento de Risco")
    
    # Configurações de risco
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ Configurações de Risco")
        
        max_drawdown = st.slider("Drawdown Máximo (%)", 0.0, 50.0, 15.0, 0.5)
        max_position_size = st.number_input("Tamanho Máximo da Posição ($)", min_value=100, value=1000, step=100)
        stop_loss_percent = st.slider("Stop Loss (%)", 0.0, 10.0, 3.0, 0.1)
        take_profit_percent = st.slider("Take Profit (%)", 0.0, 20.0, 6.0, 0.1)
        
        if st.button("💾 Salvar Configurações"):
            st.success("Configurações de risco salvas!")
    
    with col2:
        st.subheader("📊 Métricas de Risco")
        
        # Métricas de risco simuladas
        st.metric("VaR (95%)", "$125.50", "-$12.30")
        st.metric("Sharpe Ratio", "1.45", "+0.12")
        st.metric("Sortino Ratio", "1.78", "+0.08")
        st.metric("Max Drawdown", "8.5%", "-1.2%")
    
    st.divider()
    
    # Gráfico de drawdown
    st.subheader("📉 Histórico de Drawdown")
    
    # Simular dados de drawdown
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)]
    drawdown_data = [random.uniform(0, 12) for _ in range(24)]
    
    fig_drawdown = go.Figure()
    fig_drawdown.add_trace(go.Scatter(
        x=timestamps,
        y=drawdown_data,
        mode='lines',
        name='Drawdown',
        line=dict(color='red', width=2),
        fill='tozeroy'
    ))
    
    fig_drawdown.update_layout(
        title='Drawdown nas Últimas 24 Horas',
        xaxis_title='Tempo',
        yaxis_title='Drawdown (%)',
        height=300
    )
    
    st.plotly_chart(fig_drawdown, use_container_width=True)
    
    # Alertas de risco
    st.subheader("🚨 Alertas de Risco")
    
    if dashboard.dados_simulados['drawdown'] > 10:
        st.error("⚠️ Drawdown acima do limite configurado!")
    else:
        st.success("✅ Todos os parâmetros de risco dentro dos limites")

def estrategias_tab():
    """Aba de estratégias"""
    
    st.header("📈 Estratégias de Trading")
    
    # Tabs para cada estratégia
    tab_sma, tab_rsi, tab_bollinger = st.tabs(["SMA", "RSI", "Bollinger"])
    
    with tab_sma:
        st.subheader("📊 Estratégia SMA (Média Móvel Simples)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Configurações:**")
            periodo_rapido = st.number_input("Período Rápido", min_value=5, max_value=50, value=12)
            periodo_lento = st.number_input("Período Lento", min_value=20, max_value=200, value=26)
            
            st.write("**Status:**")
            st.success("✅ Ativa")
            st.info(f"Sinais gerados hoje: 3")
        
        with col2:
            st.write("**Performance:**")
            st.metric("Taxa de Acerto", "68.5%", "+2.1%")
            st.metric("P&L Total", "$245.80", "+$45.20")
            st.metric("Trades Executados", "15", "+3")
    
    with tab_rsi:
        st.subheader("📊 Estratégia RSI")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Configurações:**")
            periodo_rsi = st.number_input("Período RSI", min_value=5, max_value=50, value=14)
            nivel_sobrecompra = st.number_input("Nível Sobrecompra", min_value=60, max_value=90, value=70)
            nivel_sobrevenda = st.number_input("Nível Sobrevenda", min_value=10, max_value=40, value=30)
            
            st.write("**Status:**")
            st.warning("⏸️ Inativa")
            st.info("RSI Atual: 45.2")
        
        with col2:
            st.write("**Performance:**")
            st.metric("Taxa de Acerto", "72.3%", "+1.8%")
            st.metric("P&L Total", "$0.00", "$0.00")
            st.metric("Trades Executados", "0", "0")
    
    with tab_bollinger:
        st.subheader("📊 Estratégia Bandas de Bollinger")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Configurações:**")
            periodo_bb = st.number_input("Período", min_value=10, max_value=50, value=20)
            desvios_padrao = st.number_input("Desvios Padrão", min_value=1.0, max_value=3.0, value=2.0, step=0.1)
            modo = st.selectbox("Modo", ["Reversão", "Breakout"])
            
            st.write("**Status:**")
            st.warning("⏸️ Inativa")
            st.info("Largura das Bandas: 4.2%")
        
        with col2:
            st.write("**Performance:**")
            st.metric("Taxa de Acerto", "65.1%", "+0.5%")
            st.metric("P&L Total", "$0.00", "$0.00")
            st.metric("Trades Executados", "0", "0")

def logs_tab():
    """Aba de logs"""
    
    st.header("📋 Logs do Sistema")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nivel_log = st.selectbox("Nível", ["TODOS", "INFO", "WARNING", "ERROR", "CRITICAL"])
    
    with col2:
        modulo_log = st.selectbox("Módulo", ["TODOS", "bot_trading", "estrategias", "risk_manager", "adapters"])
    
    with col3:
        linhas_log = st.number_input("Últimas N linhas", min_value=10, max_value=1000, value=100)
    
    # Simular logs
    logs_simulados = [
        {"timestamp": datetime.now() - timedelta(seconds=i*30), 
         "nivel": random.choice(["INFO", "WARNING", "ERROR"]),
         "modulo": random.choice(["bot_trading", "estrategias", "risk_manager"]),
         "mensagem": f"Mensagem de log simulada {i+1}"}
        for i in range(50)
    ]
    
    # Aplicar filtros
    logs_filtrados = logs_simulados
    if nivel_log != "TODOS":
        logs_filtrados = [log for log in logs_filtrados if log["nivel"] == nivel_log]
    if modulo_log != "TODOS":
        logs_filtrados = [log for log in logs_filtrados if log["modulo"] == modulo_log]
    
    # Mostrar logs
    st.subheader(f"📄 Logs ({len(logs_filtrados)} entradas)")
    
    for log in logs_filtrados[:linhas_log]:
        timestamp_str = log["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        
        if log["nivel"] == "ERROR":
            st.error(f"[{timestamp_str}] {log['modulo']} - {log['mensagem']}")
        elif log["nivel"] == "WARNING":
            st.warning(f"[{timestamp_str}] {log['modulo']} - {log['mensagem']}")
        else:
            st.info(f"[{timestamp_str}] {log['modulo']} - {log['mensagem']}")
    
    # Botão para limpar logs
    if st.button("🗑️ Limpar Logs"):
        st.success("Logs limpos com sucesso!")

# Auto-refresh
if st.session_state.bot_running:
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()
