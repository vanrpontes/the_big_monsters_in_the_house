import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. Configuração da página
st.set_page_config(page_title="The Big Monster's Dashboard", layout="wide", page_icon="👹")

st.title("The Big Monster's in the House")
st.markdown("---")

url = st.secrets["connections"]["gsheets"]["spreadsheet"]

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # AJUSTE 1: TTL reduzido para 5 segundos para refletir mudanças rápidas (ideal para o vídeo)
    df_raw = conn.read(spreadsheet=url, ttl="5s") 
    df_raw.columns = df_raw.columns.str.strip().str.lower()
    
    # --- TRATAMENTO DE DADOS ---
    df_raw['data'] = pd.to_datetime(df_raw['data'], dayfirst=True)
    
    # Datas de controle
    hoje = pd.Timestamp.now().normalize()
    inicio_janela = hoje - timedelta(days=7)

    # Tradução dos dias da semana
    dias_pt = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }

    # AJUSTE 2: Deixamos 'atividade' como numeric mas sem fillna(0) global 
    # para diferenciar o que é falta (0) do que é apenas dia não preenchido (NaN)
    df_raw['atividade'] = pd.to_numeric(df_raw['atividade'], errors='coerce')
    df_raw['peso'] = pd.to_numeric(df_raw['peso'], errors='coerce')
    
    if 'diasemana' in df_raw.columns:
        df_raw['diasemana_pt'] = df_raw['diasemana'].map(dias_pt)
    else:
        df_raw['diasemana_pt'] = df_raw['data'].dt.day_name().map(dias_pt)

    # AJUSTE 3: Filtro unificado até HOJE (removemos o 'ontem')
    df_historico = df_raw[df_raw['data'] <= hoje].copy()

    # --- CÁLCULOS ---
    # Soma de treinos (ignora vazios automaticamente)
    treinos_janela = df_historico[(df_historico['data'] >= inicio_janela)]['atividade'].sum()
    treinos_total = int(df_historico['atividade'].sum())
    
    # Peso atual (último registro válido até hoje)
    peso_atual = df_historico['peso'].dropna().iloc[-1] if not df_historico['peso'].dropna().empty else 89.0

    # --- DASHBOARD FRONT-END ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Treinos Realizados", f"{treinos_total}", "Meta: 208")
        
    with col2:
        falta_peso = float(peso_atual) - 74.0
        st.metric("Peso Atual", f"{peso_atual:.1f} kg", f"{falta_peso:.1f} kg para a meta", delta_color="inverse")

    with col3:
        if treinos_janela >= 5:
            status_msg, cor = "TÁ SAINDO DA JAULA O MONSTRO! 🔥", "#FF4B4B"
        elif treinos_janela >= 3:
            status_msg, cor = "MONSTRO ATIVO 🦾", "#00FF00"
        else:
            status_msg, cor = "SNORLAX HIBERNANDO 😴", "#777777"
        
        st.markdown(f"<p style='color: #888; font-size: 14px; margin-bottom: 5px;'>Status Atual (Tempo Real)</p>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: {cor}; margin-top: -15px;'>{status_msg}</h3>", unsafe_allow_html=True)
        st.caption(f"Base