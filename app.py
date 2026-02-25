import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Barbino", layout="wide")

def conectar():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_info = json.loads(st.secrets["gcp_service_account"])
    else:
        with open("credentials.json") as f:
            creds_info = json.load(f)
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# --- CARREGAMENTO ---
try:
    client = conectar()
    sheet = client.open("FINANÇAS").worksheet("FINANÇAS")
    dados = sheet.get("A1:G3000") 
    df = pd.DataFrame(dados[1:], columns=["ANO", "MÊS", "STATUS", "DATA_VENC", "TIPO", "VALOR", "DESCRIÇÃO"])

    def para_float(v):
        if not v or str(v).strip() == "": return 0.0
        v = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try: return float(v)
        except: return 0.0

    df['VALOR_NUM'] = df['VALOR'].apply(para_float)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS + NOVO LANÇAMENTO) ---
with st.sidebar:
    st.header("🗓️ Filtros")
    meses = df['MÊS'].unique()
    mes_ref = st.selectbox("Mês de Referência:", meses, index=len(meses)-1)
    
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("novo_sidebar"):
        n_tipo = st.selectbox("Tipo", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO", "INVESTIMENTO"])
        n_valor = st.text_input("Valor (Ex: 1.500,00)")
        n_desc = st.text_input("Descrição")
        if st.form_submit_button("Lançar na Planilha"):
            sheet.append_row(["2026", mes_ref, "", "", n_tipo, n_valor, n_desc.upper()])
            st.success("Lançado!")
            st.rerun()

# --- CÁLCULOS DO DASHBOARD ---
df_mes = df[df['MÊS'] == mes_ref]

# Lógica solicitada: Saldo Liquido bate com R$ 3.313,22
# RESGATE e SALDO entram como valores positivos no caixa
v_entrada = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
v_saldo_ant = df_mes[df_mes['TIPO'] == 'SALDO']['VALOR_NUM'].sum()
v_resgate = df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum()
v_saida = abs(df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum())
v_invest = abs(df_mes[df_mes['TIPO'] == 'INVESTIMENTO']['VALOR_NUM'].sum())

saldo_liquido = (v_entrada + v_saldo_ant + v_resgate) - (v_saida + v_invest)

# --- VISUALIZAÇÃO ---
st.title(f"📊 Dashboard Barbino - {mes_ref}")

# Métricas
m1, m2, m3, m4 = st.columns(4)
m1.metric("Entradas + Saldo Ant", f"R$ {v_entrada + v_saldo_ant:,.2f}")
m2.metric("Saídas (Gastos)", f"R$ {v_saida:,.2f}")
m3.metric("Resgates/Aportes", f"R$ {v_resgate - v_invest:,.2f}")
m4.metric("SALDO LÍQUIDO", f"R$ {saldo_liquido:,.2f}")

st.divider()

# Gráfico Híbrido: Entradas (Barras) e Cartões (Linha)
st.subheader("📈 Entradas Mensais vs Gastos em Cartão")
df_anual_ent = df[df['TIPO'] == 'ENTRADA'].groupby('MÊS')['VALOR_NUM'].sum()
df_anual_cart = df[df['DESCRIÇÃO'].str.contains("CARTÃO", na=False)].groupby('MÊS')['VALOR_NUM'].apply(lambda x: abs(x.sum()))

fig = go.Figure()
fig.add_trace(go.Bar(x=df_anual_ent.index, y=df_anual_ent.values, name='Total Entradas', marker_color='#00b4d8'))
fig.add_trace(go.Scatter(x=df_anual_cart.index, y=df_anual_cart.values, name='Gastos Cartão', line=dict(color='#ff4b4b', width=4)))
st.plotly_chart(fig, use_container_width=True)

# Distribuição do Mês (%)
st.subheader("🍕 Distribuição do Mês")
labels_pizza = ['ENTRADA', 'SALDO', 'RESGATE', 'SAÍDA', 'INVESTIMENTO']
valores_pizza = [v_entrada, v_saldo_ant, v_resgate, v_saida, v_invest]
fig_pie = go.Figure(data=[go.Pie(labels=labels_pizza, values=valores_pizza, hole=.3)])
st.plotly_chart(fig_pie)

# Tabela de Edição
st.divider()
st.subheader("📑 Gestão da Planilha")
st.dataframe(df_mes[["TIPO", "VALOR", "DESCRIÇÃO", "STATUS"]], use_container_width=True)

with st.expander("📝 Editar ou Excluir"):
    linha_idx = st.selectbox("Selecione a linha:", options=df_mes.index, 
                             format_func=lambda x: f"{df_mes.loc[x, 'DESCRIÇÃO']} ({df_mes.loc[x, 'VALOR']})")
    
    c_edit1, c_edit2 = st.columns(2)
    with c_edit1:
        if st.button("🗑️ Excluir permanentemente"):
            sheet.delete_rows(int(linha_idx) + 2)
            st.success("Excluído!")
            st.rerun()
    with c_edit2:
        novo_v = st.text_input("Novo Valor", value=df_mes.loc[linha_idx, 'VALOR'])
        if st.button("💾 Salvar Alteração"):
            sheet.update_cell(int(linha_idx) + 2, 6, novo_v)
            st.success("Salvo!")
            st.rerun()
