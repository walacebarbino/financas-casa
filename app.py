import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Barbino 2026", layout="wide", page_icon="💰")

def conectar():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Tenta carregar dos secrets (Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        creds_info = json.loads(st.secrets["gcp_service_account"])
    else:
        with open("credentials.json") as f:
            creds_info = json.load(f)
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# --- CARREGAMENTO E LIMPEZA ---
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
    st.error(f"Erro de conexão ou planilha: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS + NOVO LANÇAMENTO) ---
with st.sidebar:
    st.title("⚙️ Painel de Controle")
    meses_disponiveis = df['MÊS'].unique()
    mes_selecionado = st.selectbox("Selecione o Mês:", meses_disponiveis, index=len(meses_disponiveis)-1)
    
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("sidebar_form"):
        n_tipo = st.selectbox("Tipo:", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO", "INVESTIMENTO"])
        n_valor = st.text_input("Valor (Ex: 1.200,50):")
        n_desc = st.text_input("Descrição:")
        if st.form_submit_button("Enviar para Planilha"):
            sheet.append_row(["2026", mes_selecionado, "", "", n_tipo, n_valor, n_desc.upper()])
            st.success("Lançado com sucesso!")
            st.rerun()

# --- LÓGICA FINANCEIRA (BATENDO COM R$ 3.313,22) ---
df_mes = df[df['MÊS'] == mes_selecionado]

# Soma de entradas de caixa
v_entrada = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
v_saldo_ant = df_mes[df_mes['TIPO'] == 'SALDO']['VALOR_NUM'].sum()
v_resgate = df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum() # Resgate soma no caixa

# Soma de saídas de caixa
v_saida = abs(df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum())
v_invest = abs(df_mes[df_mes['TIPO'] == 'INVESTIMENTO']['VALOR_NUM'].sum())

# Cálculo Final
saldo_real = (v_entrada + v_saldo_ant + v_resgate) - (v_saida + v_invest)

# --- DASHBOARD VISUAL ---
st.title(f"📊 Dashboard Financeiro - {mes_selecionado}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Entradas + Saldo Ant", f"R$ {v_entrada + v_saldo_ant:,.2f}")
col2.metric("Saídas Totais", f"R$ {v_saida:,.2f}")
col3.metric("Resgates", f"R$ {v_resgate:,.2f}")
col4.metric("SALDO LÍQUIDO", f"R$ {saldo_real:,.2f}")

st.divider()

# --- GRÁFICO HÍBRIDO ---
st.subheader("📈 Entradas Mensais vs Gastos em Cartão")
df_anual_ent = df[df['TIPO'] == 'ENTRADA'].groupby('MÊS')['VALOR_NUM'].sum()
# Busca por "CARTÃO" na descrição
df_cartoes = df[df['DESCRIÇÃO'].str.contains("CARTÃO", na=False)].groupby('MÊS')['VALOR_NUM'].apply(lambda x: abs(x.sum()))

fig = go.Figure()
# Barras para Entradas
fig.add_trace(go.Bar(x=df_anual_ent.index, y=df_anual_ent.values, name='Total Recebido', marker_color='#00b4d8'))
# Linha para Cartões
fig.add_trace(go.Scatter(x=df_cartoes.index, y=df_cartoes.values, name='Fatura Cartões', line=dict(color='#ff4b4b', width=4)))
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# --- DISTRIBUIÇÃO EM PIZZA ---
st.subheader("🍕 Distribuição do Mês (%)")
# Agrupamos todos os tipos solicitados
pizza_data = df_mes.groupby('TIPO')['VALOR_NUM'].sum().abs()
fig_pie = go.Figure(data=[go.Pie(labels=pizza_data.index, values=pizza_data.values, hole=.3)])
fig_pie.update_traces(textinfo='percent+value')
st.plotly_chart(fig_pie)

# --- GESTÃO DA PLANILHA ---
st.divider()
st.subheader("📑 Edição e Exclusão de Linhas")
st.dataframe(df_mes[["TIPO", "VALOR", "DESCRIÇÃO", "STATUS"]], use_container_width=True)

with st.expander("🛠️ Ações de Edição"):
    linha_para_editar = st.selectbox("Selecione a linha:", options=df_mes.index, 
                                     format_func=lambda x: f"{df_mes.loc[x, 'DESCRIÇÃO']} | {df_mes.loc[x, 'VALOR']}")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🗑️ Excluir Linha Selecionada"):
            sheet.delete_rows(int(linha_para_editar) + 2)
            st.warning("Linha removida da planilha!")
            st.rerun()
    with c_btn2:
        novo_status = st.text_input("Atualizar Status:", value=df_mes.loc[linha_para_editar, 'STATUS'])
        if st.button("💾 Salvar Novo Status"):
            # Coluna 3 é o Status na planilha
            sheet.update_cell(int(linha_para_editar) + 2, 3, novo_status.upper())
            st.success("Status atualizado!")
            st.rerun()
