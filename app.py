import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Financeiro Barbino", layout="wide", page_icon="🏦")

def conectar():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# --- PROCESSAMENTO DE DADOS ---
try:
    client = conectar()
    sheet = client.open("FINANÇAS").worksheet("FINANÇAS")
    # Lemos apenas A até G para garantir performance e evitar erros de colunas extras
    dados = sheet.get("A1:G3000") 
    df = pd.DataFrame(dados[1:], columns=["ANO", "MÊS", "STATUS", "DATA_VENC", "TIPO", "VALOR", "DESCRIÇÃO"])

    # Função para converter os valores brasileiros (R$ 1.200,50) em números para o Python
    def para_float(v):
        if not v or str(v).strip() == "": return 0.0
        v = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try: return float(v)
        except: return 0.0

    df['VALOR_NUM'] = df['VALOR'].apply(para_float)
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🗓️ Período de Análise")
meses = df['MÊS'].unique()
mes_selecionado = st.sidebar.selectbox("Selecione o Mês:", meses, index=len(meses)-1)

# Filtramos os dados para o dashboard
df_mes = df[df['MÊS'] == mes_selecionado]

# --- LÓGICA DE CÁLCULOS (INTELIGÊNCIA DO SISTEMA) ---
# Separamos os dados por categoria baseados na sua descrição
entradas = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
saidas = abs(df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum())
investimentos = abs(df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum())

# Busca automática por palavras-chave
cartoes = abs(df_mes[df_mes['DESCRIÇÃO'].str.contains("CARTÃO", na=False, case=False)]['VALOR_NUM'].sum())
financiamentos = abs(df_mes[df_mes['DESCRIÇÃO'].str.contains("FINANC", na=False, case=False)]['VALOR_NUM'].sum())
educacao = abs(df_mes[df_mes['DESCRIÇÃO'].str.contains("EDUCAÇÃO|FACULDADE|ESCOLA", na=False, case=False)]['VALOR_NUM'].sum())

# --- DASHBOARD VISUAL ---
st.title(f"🏦 Controle Barbino - {mes_selecionado}")

# Linha 1: Métricas Principais
m1, m2, m3, m4 = st.columns(4)
m1.metric("Receitas", f"R$ {entradas:,.2f}")
m2.metric("Despesas", f"R$ {saidas:,.2f}", delta=f"-{saidas:,.2f}", delta_color="inverse")
m3.metric("Investido", f"R$ {investimentos:,.2f}")
saldo = entradas - saidas - investimentos
m4.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta="Em conta")

st.divider()

# Linha 2: Resumo de Gastos Fixos/Grandes
st.subheader("📊 Resumo de Grandes Grupos")
c1, c2, c3 = st.columns(3)
with c1:
    st.info(f"💳 **Cartões:** R$ {cartoes:,.2f}")
with c2:
    st.warning(f"🏠 **Financ/Cons:** R$ {financiamentos:,.2f}")
with c3:
    st.success(f"🎓 **Educação:** R$ {educacao:,.2f}")

st.divider()

# Linha 3: Gráficos
g1, g2 = st.columns([2, 1])
with g1:
    st.subheader("📅 Evolução Mensal de Entradas")
    evolucao = df[df['TIPO'] == 'ENTRADA'].groupby('MÊS')['VALOR_NUM'].sum()
    st.line_chart(evolucao)

with g2:
    st.subheader("🍕 Distribuição do Mês")
    labels = ['Saldo', 'Saídas', 'Investido']
    valores_pizza = [max(0, saldo), saidas, investimentos]
    # Usando gráfico de barras simples para representar a proporção
    st.bar_chart(pd.DataFrame(valores_pizza, index=labels))

# --- GESTÃO DE DADOS ---
st.divider()
with st.expander("🛠️ Adicionar novo lançamento à planilha"):
    with st.form("form_novo"):
        col_a, col_b, col_c = st.columns(3)
        novo_mes = col_a.text_input("Mês (ex: jan/26)", value=mes_selecionado)
        novo_tipo = col_b.selectbox("Tipo", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO"])
        novo_valor = col_c.text_input("Valor (ex: 1.250,00)")
        novo_desc = st.text_input("Descrição (Ex: CARTÃO ITAU, PICPAY, MOTO)")
        
        if st.form_submit_button("Lançar na Planilha"):
            # Envia para a planilha mantendo o padrão
            sheet.append_row(["2026", novo_mes, "OK", "", novo_tipo, novo_valor, novo_desc.upper()])
            st.success("Lançado com sucesso! Atualize a página.")
            st.rerun()
