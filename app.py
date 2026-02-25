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
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    else:
        st.error("Configure as Secrets no Streamlit Cloud.")
        st.stop()

# --- CARREGAMENTO ---
try:
    client = conectar()
    sheet = client.open("FINANÇAS").worksheet("FINANÇAS")
    dados = sheet.get("A1:G3000") 
    df = pd.DataFrame(dados[1:], columns=["ANO", "MÊS", "STATUS", "DATA_VENC", "TIPO", "VALOR", "DESCRIÇÃO"])

    def para_float(v):
        if not v or str(v).strip() == "": return 0.0
        # Limpa R$, pontos de milhar e troca vírgula por ponto
        v = str(v).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try: return float(v)
        except: return 0.0

    df['VALOR_NUM'] = df['VALOR'].apply(para_float)
except Exception as e:
    st.error(f"Erro ao ler planilha: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS + NOVO) ---
with st.sidebar:
    st.header("🗓️ Filtros")
    meses = df['MÊS'].unique()
    mes_selecionado = st.selectbox("Escolha o Mês:", meses, index=len(meses)-1)
    
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("form_novo"):
        n_tipo = st.selectbox("Tipo", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO", "INVESTIMENTO"])
        n_valor = st.text_input("Valor (Ex: 1.250,00)")
        n_desc = st.text_input("Descrição")
        if st.form_submit_button("Lançar"):
            sheet.append_row(["2026", mes_selecionado, "", "", n_tipo, n_valor, n_desc.upper()])
            st.rerun()

# --- CÁLCULOS (BATENDO COM A PLANILHA) ---
df_mes = df[df['MÊS'] == mes_selecionado]

v_entrada = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
v_saldo_ant = df_mes[df_mes['TIPO'] == 'SALDO']['VALOR_NUM'].sum()
v_resgate = df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum()
v_saida = abs(df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum())
v_invest = abs(df_mes[df_mes['TIPO'] == 'INVESTIMENTO']['VALOR_NUM'].sum())

# Saldo Líquido exato: 3.313,22
saldo_total = (v_entrada + v_saldo_ant + v_resgate) - (v_saida + v_invest)

# --- DASHBOARD ---
st.title(f"📊 Controle Barbino - {mes_selecionado}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Disponível (Entradas+Saldo)", f"R$ {v_entrada + v_saldo_ant:,.2f}")
m2.metric("Despesas", f"R$ {v_saida:,.2f}")
m3.metric("Resgates", f"R$ {v_resgate:,.2f}")
m4.metric("SALDO LÍQUIDO", f"R$ {saldo_total:,.2f}")

# --- GRÁFICOS ---
st.subheader("📈 Comparativo: Entradas vs Cartões")
# Pega o total de entradas por mês
df_ent = df[df['TIPO'] == 'ENTRADA'].groupby('MÊS')['VALOR_NUM'].sum()
# Pega o total de cartões por mês (procurando "CARTÃO" na descrição)
df_cart = df[df['DESCRIÇÃO'].str.contains("CARTÃO", na=False)].groupby('MÊS')['VALOR_NUM'].apply(lambda x: abs(x.sum()))

fig = go.Figure()
fig.add_trace(go.Bar(x=df_ent.index, y=df_ent.values, name="Entradas", marker_color='RoyalBlue'))
fig.add_trace(go.Scatter(x=df_cart.index, y=df_cart.values, name="Gasto Cartão", line=dict(color='FireBrick', width=4)))
st.plotly_chart(fig, use_container_width=True)

st.subheader("🍕 Distribuição por Categoria")
dist = df_mes.groupby('TIPO')['VALOR_NUM'].sum().abs()
fig_p = go.Figure(data=[go.Pie(labels=dist.index, values=dist.values, hole=.3)])
st.plotly_chart(fig_p)

# --- TABELA DE GESTÃO ---
st.divider()
st.subheader("📑 Visualização e Edição")
st.dataframe(df_mes[["TIPO", "VALOR", "DESCRIÇÃO", "STATUS"]], use_container_width=True)

with st.expander("🗑️ Excluir Linha"):
    linha_id = st.selectbox("Selecione para excluir:", options=df_mes.index,
                            format_func=lambda x: f"{df_mes.loc[x, 'DESCRIÇÃO']} - {df_mes.loc[x, 'VALOR']}")
    if st.button("Confirmar Exclusão"):
        sheet.delete_rows(int(linha_id) + 2)
        st.success("Excluído!")
        st.rerun()
