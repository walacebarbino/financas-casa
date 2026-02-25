import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Barbino 2026", layout="wide", page_icon="💰")

def conectar_google():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# --- INICIALIZAÇÃO E LIMPEZA DE DADOS ---
try:
    client = conectar_google()
    sheet = client.open("FINANÇAS").get_worksheet(0)
    
    # Lemos os dados
    valores = sheet.get("A1:G1000")
    cabecalho = ["ANO", "MÊS", "STATUS", "DATA VENC", "TIPO", "VALOR", "DESCRIÇÃO"]
    df = pd.DataFrame(valores[1:], columns=cabecalho)

    # Limpeza para cálculos: Transformar "1.500,00" em número real
    def limpar_valor(v):
        if not v: return 0.0
        return float(v.replace('.', '').replace(',', '.'))

    df['VALOR_NUM'] = df['VALOR'].apply(limpar_valor)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.title("🔍 Filtros de Visualização")
mes_selecionado = st.sidebar.selectbox("Escolha o Mês:", options=df['MÊS'].unique())
df_mes = df[df['MÊS'] == mes_selecionado]

# --- PAINEL PRINCIPAL (DASHBOARD) ---
st.title(f"📊 Controle Financeiro - {mes_selecionado}")

# Cálculos para os Cards
entradas = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
saidas = df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum()
investimentos = df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum()
saldo_final = entradas - saidas

# Exibição dos Cards (Métricas)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Entradas", f"R$ {entradas:,.2f}")
c2.metric("Total Saídas", f"R$ {saidas:,.2f}", delta_color="inverse")
c3.metric("Investimentos/Resgates", f"R$ {investimentos:,.2f}")
c4.metric("Saldo do Mês", f"R$ {saldo_final:,.2f}")

st.divider()

# --- ANÁLISE DETALHADA ---
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("💳 Gastos por Categoria (Cartões/Financ)")
    # Agrupamos por palavras-chave na descrição
    df_mes_saida = df_mes[df_mes['TIPO'] == 'SAÍDA']
    st.bar_chart(df_mes_saida.set_index('DESCRIÇÃO')['VALOR_NUM'])

with col_graf2:
    st.subheader("📅 Resumo Anual (Geral)")
    resumo_anual = df.groupby('MÊS')['VALOR_NUM'].sum()
    st.line_chart(resumo_anual)

# --- ABA DE GESTÃO (EDITAR/INCLUIR) ---
st.divider()
expander = st.expander("📝 Gerenciar Dados (Adicionar ou Editar Linhas)")
with expander:
    op = st.radio("Ação:", ["Novo", "Editar"], horizontal=True)
    
    if op == "Novo":
        with st.form("novo"):
            cols = st.columns(3)
            v_ano = cols[0].text_input("ANO", "2026")
            v_mes = cols[1].text_input("MÊS", mes_selecionado)
            v_status = cols[2].selectbox("STATUS", ["PENDENTE", "OK"])
            v_tipo = st.selectbox("TIPO", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO"])
            v_desc = st.text_input("DESCRIÇÃO")
            v_valor = st.text_input("VALOR (Ex: 150,00)")
            
            if st.form_submit_button("Salvar na Planilha"):
                sheet.append_row([v_ano, v_mes, v_status, "", v_tipo, v_valor, v_desc])
                st.success("Adicionado!")
                st.rerun()
    else:
        # Lógica de edição semelhante à anterior...
        idx = st.selectbox("Selecione para editar:", options=df_mes.index, 
                           format_func=lambda x: f"{df_mes.loc[x, 'DESCRIÇÃO']} ({df_mes.loc[x, 'VALOR']})")
        # (Campos de edição aqui...)
