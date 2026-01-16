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


    # Criando as colunas necessárias
    df_raw['atividade'] = pd.to_numeric(df_raw['atividade'], errors='coerce')
    df_raw['peso'] = pd.to_numeric(df_raw['peso'], errors='coerce')
   
    if 'diasemana' in df_raw.columns:
        df_raw['diasemana_pt'] = df_raw['diasemana'].map(dias_pt)
    else:
        df_raw['diasemana_pt'] = df_raw['data'].dt.day_name().map(dias_pt)


    # --- LÓGICA DE CORTE CORRIGIDA ---
    # Verifica se HOJE tem dado preenchido (não é NaN)
    registro_hoje = df_raw[df_raw['data'] == hoje]
    
    if not registro_hoje.empty and pd.notna(registro_hoje['atividade'].iloc[0]):
        # Se HOJE tem valor (0 ou 1), inclui até HOJE
        data_corte = hoje
        nota_fechamento = ""
    else:
        # Se HOJE está vazio, inclui apenas até ONTEM
        data_corte = ontem
        nota_fechamento = " (Fechado D-1)"
    
    # Dataset filtrado baseado na regra acima
    df_historico = df_raw[df_raw['data'] <= data_corte].copy()
    
    # Preenche NaN com 0 APENAS no dataset filtrado
    df_historico['atividade'] = df_historico['atividade'].fillna(0)
    
    
    # --- FILTROS E CÁLCULOS ---
    treinos_janela = df_historico[(df_historico['data'] >= inicio_janela)]['atividade'].sum()
    treinos_total = int(df_historico['atividade'].sum())
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
    
        st.markdown(f"<p style='color: #888; font-size: 14px; margin-bottom: 5px;'>Status Atual (D-7)</p>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: {cor}; margin-top: -15px;'>{status_msg}</h3>", unsafe_allow_html=True)
        st.caption(f"Baseado em {int(treinos_janela)} treinos nos últimos 7 dias.")

    st.markdown("---")

    # --- HEATMAP ESTILO GITHUB ---
    st.subheader("🔥 Mapa de Calor de Consistência (Semanal)")
   
    df_heat = df_historico.copy()
    df_heat['semana'] = df_heat['data'].dt.isocalendar().week
    df_heat['dia_num'] = df_heat['data'].dt.dayofweek
   
    fig = px.imshow(
        df_heat.pivot_table(index='dia_num', columns='semana', values='atividade', aggfunc='sum').fillna(0),
        labels=dict(x="Semana do Ano", y="Dia da Semana", color="Treinou"),
        x=df_heat.pivot_table(index='dia_num', columns='semana', values='atividade').columns,
        y=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
        color_continuous_scale=[[0, "#161b22"], [1, "#39d353"]],
    )

    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    # Ajuste do eixo X para pular de 4 em 4
    min_sem = int(df_heat['semana'].min())
    fig.update_xaxes(
        side="bottom",
        showgrid=False,
        tickmode='linear',
        tick0=min_sem,
        dtick=4
    )
    fig.update_yaxes(showgrid=False)

  
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")
   
    # --- TABELA VISUAL ---
    df_visual = df_historico.copy()
    df_visual['data_formatada'] = df_visual['data'].dt.strftime('%d-%m-%Y')
    df_visual['treino'] = df_visual['atividade'].map({1: '✅ TREINEI', 0: '❌ FALTEI'})
   
    filtro = st.radio("Filtrar histórico:", ["Todos os dias", "Apenas dias de treino"], horizontal=True)
    if filtro == "Apenas dias de treino":
        df_visual = df_visual[df_visual['atividade'] == 1]

    st.subheader(f"🗓️ Histórico de Atividades{nota_fechamento}")
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