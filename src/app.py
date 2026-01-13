import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuração da página
st.set_page_config(page_title="The Big Monster's Dashboard", layout="wide", page_icon="👹")

st.title("The Big Monster's in the House")
st.markdown("---")

url = st.secrets["connections"]["gsheets"]["spreadsheet"]

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=url, ttl="10m")
    df_raw.columns = df_raw.columns.str.strip().str.lower()
    
    # --- TRATAMENTO DE DADOS ---
    df_raw['data'] = pd.to_datetime(df_raw['data'], dayfirst=True)
    
    # Datas de controle
    hoje = pd.Timestamp.now().normalize()
    ontem = hoje - timedelta(days=1)
    inicio_janela = hoje - timedelta(days=7)

    # Tradução dos dias da semana
    dias_pt = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }

    # Criando as colunas necessárias ANTES de qualquer filtro
    df_raw['atividade'] = pd.to_numeric(df_raw['atividade'], errors='coerce').fillna(0)
    df_raw['peso'] = pd.to_numeric(df_raw['peso'], errors='coerce')
    if 'diasemana' in df_raw.columns:
        df_raw['diasemana_pt'] = df_raw['diasemana'].map(dias_pt)
    else:
        df_raw['diasemana_pt'] = df_raw['data'].dt.day_name().map(dias_pt)

    # --- FILTROS PARA STATUS E TABELA (Até Ontem) ---
    df_historico = df_raw[df_raw['data'] <= ontem].copy()
    treinos_janela = df_historico[(df_historico['data'] >= inicio_janela)]['atividade'].sum()

    # --- CÁLCULOS KPI ---
    treinos_total = int(df_raw[df_raw['data'] <= hoje]['atividade'].sum())
    # Peso atual pode considerar hoje se houver registro
    peso_atual = df_raw[df_raw['data'] <= hoje]['peso'].dropna().iloc[-1] if not df_raw['peso'].dropna().empty else 89.0

    # --- DASHBOARD FRONT-END (Layout Alinhado) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Treinos Realizados", f"{treinos_total}", "Meta: 208")
        
    with col2:
        falta_peso = float(peso_atual) - 74.0
        st.metric("Peso Atual", f"{peso_atual:.1f} kg", f"{falta_peso:.1f} kg para a meta", delta_color="inverse")

    with col3:
        # Definindo Status e Cor
        if treinos_janela >= 5:
            status_msg, cor = "TÁ SAINDO DA JAULA O MONSTRO! 🔥", "#FF4B4B" # Vermelho/Laranja
        elif treinos_janela >= 3:
            status_msg, cor = "MONSTRO ATIVO 🦾", "#00FF00" # Verde
        else:
            status_msg, cor = "SNORLAX HIBERNANDO 😴", "#777777" # Cinza
        
        # Estilizando o Status para ficar no mesmo nível visual das métricas
        st.markdown(f"<p style='color: #888; font-size: 14px; margin-bottom: 5px;'>Status Atual (D-7)</p>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: {cor}; margin-top: -15px;'>{status_msg}</h3>", unsafe_allow_html=True)
        st.caption(f"Baseado em {int(treinos_janela)} treinos nos últimos 7 dias.")

    st.markdown("---")
    
    # --- TABELA VISUAL ---
    df_visual = df_historico.copy()
    df_visual['data_formatada'] = df_visual['data'].dt.strftime('%d-%m-%Y')
    df_visual['treino'] = df_visual['atividade'].map({1: '✅ TREINEI', 0: '❌ FALTEI'})
    
    filtro = st.radio("Filtrar histórico:", ["Todos os dias", "Apenas dias de treino"], horizontal=True)
    
    if filtro == "Apenas dias de treino":
        df_visual = df_visual[df_visual['atividade'] == 1]

    st.subheader("🗓️ Histórico de Atividades (Fechado D-1)")
    
    # Garantindo que as colunas existem antes de exibir para não dar erro de Index
    colunas_exibicao = ['data_formatada', 'diasemana_pt', 'treino', 'peso']
    
    st.dataframe(
        df_visual[colunas_exibicao].sort_values(by='data_formatada', ascending=False), 
        column_config={
            "data_formatada": "Data",
            "diasemana_pt": "Dia da Semana",
            "treino": "Situação",
            "peso": "Peso (kg)"
        },
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Erro detectado: {e}")
    st.info("Dica: Verifique se as colunas na planilha estão com os nomes corretos.")