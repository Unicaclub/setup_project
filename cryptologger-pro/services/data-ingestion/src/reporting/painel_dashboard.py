"""
Painel visual de compliance e alertas ao vivo.
"""
import streamlit as st
import pandas as pd

class PainelDashboard:
    """
    Exibe alertas, scores de risco e gráficos em tempo real.
    """
    def __init__(self, alertas, relatorios):
        self.alertas = alertas
        self.relatorios = relatorios

    def exibir(self):
        st.title("Painel de Compliance - CryptoLogger Pro")
        st.subheader("Alertas Recentes")
        df_alertas = pd.DataFrame(self.alertas)
        st.dataframe(df_alertas)
        st.subheader("Gráficos de Score de Risco")
        if not df_alertas.empty:
            st.bar_chart(df_alertas['score'])
        st.subheader("Relatórios Regulatório Recentes")
        df_rel = pd.DataFrame(self.relatorios)
        st.dataframe(df_rel)
