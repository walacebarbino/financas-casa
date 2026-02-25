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
    creds_info = json.loads(st.secrets["gcp_service_account"])
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
    st.error(f"Erro: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS + NOVO LANÇAMENTO) ---
with st.sidebar:
    st.header("🗓️ Filtros")
    meses = df['MÊS'].unique()
    mes_selecionado = st.selectbox("Mês de Referência:", meses, index=len(meses)-1)
    
    st.divider()
    st.header("➕ Novo Lançamento")
    with st.form("novo_sidebar"):
        n_tipo = st.selectbox("Tipo", ["ENTRADA", "SAÍDA", "RESGATE", "SALDO", "INVESTIMENTO"])
        n_valor = st.text_input("Valor (Ex: 1.500,00)")
        n_desc = st.text_input("Descrição")
        if st.form_submit_button("Lançar na Planilha"):
            sheet.append_row(["2026", mes_selecionado, "OK", "", n_tipo, n_valor, n_desc.upper()])
            st.success("Lançado!")
            st.rerun()

# --- LÓGICA FINANCEIRA (BATENDO COM A PLANILHA) ---
df_mes = df[df['MÊS'] == mes_selecionado]

# Cálculos Precisos
v_entrada = df_mes[df_mes['TIPO'] == 'ENTRADA']['VALOR_NUM'].sum()
v_saldo_ant = df_mes[df_mes['TIPO'] == 'SALDO']['VALOR_NUM'].sum()
v_resgate = df_mes[df_mes['TIPO'] == 'RESGATE']['VALOR_NUM'].sum()
v_saida = abs(df_mes[df_mes['TIPO'] == 'SAÍDA']['VALOR_NUM'].sum())
v_invest = abs(df_mes[df_mes['TIPO'] == 'INVESTIMENTO']['VALOR_NUM'].sum())

# Saldo Líquido = (Entradas + Saldo Ant + Resgates) - (Saídas + Investimentos)
saldo_real = (v_entrada + v_saldo_ant + v_resgate) - (v_saida + v_invest)

# --- DASHBOARD VISUAL ---
st.title(f"📊 Dashboard Barbino - {mes_selecionado}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Entradas + Saldo Ant", f"R$ {v_entrada + v_saldo_ant:,.2f}")
c2.metric("Saídas (Gastos)", f"R$ {v_saida:,.2f}", delta_color="inverse")
c3.metric("Resgates", f"R$ {v_resgate:,.2f}")
c4.metric("SALDO LÍQUIDO", f"R$ {saldo_real:,.2f}", delta="Bate com Planilha")

st.divider()

# --- GRÁFICO HÍBRIDO (ENTRADAS VS CARTÕES) ---
st.subheader("📈 Desempenho Mensal: Entradas vs Gastos em Cartão")

# Preparar dados para o gráfico anual
df_anual = df.groupby(['MÊS', 'TIPO'])['VALOR_NUM'].sum().unstack(fill_value=0)
df_cartoes = df[df['DESCRIÇÃO'].str.contains("CARTÃO", na=False)].groupby('MÊS')['VALOR_NUM'].apply(lambda x: abs(x.sum()))

fig = go.Figure()
# Barras para Entradas
fig.add_trace(go.Bar(x=df_anual.index, y=df_anual['ENTRADA'], name='Entradas', marker_color='#00b4d8'))
# Linha para Cartões
fig.add_trace(go.Scatter(x=df_cartoes.index, y=df_cartoes.values, name='Gastos Cartão', line=dict(color='#ff4b4b', width=4)))

fig.update_layout(barmode='group', template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# --- DISTRIBUIÇÃO DO MÊS (PIZZA COM %) ---
st.subheader("🍕 Distribuição por Tipo")
dist_data = df_mes.groupby('TIPO')['VALOR_NUM'].sum().abs()
fig_pie = go.Figure(data=[go.Pie(labels=dist_data.index, values=dist_data.values, hole=.3)])
st.plotly_chart(fig_pie)

# --- TABELA DE EDIÇÃO E EXCLUSÃO ---
st.divider()
st.subheader("📑 Visualização e Edição da Planilha")

# Exibir dataframe com seleção para edição/exclusão
st.dataframe(df_mes[["TIPO", "VALOR", "DESCRIÇÃO", "STATUS"]], use_container_width=True)

with st.expander("📝 Editar ou Excluir Linha Específica"):
    linha_idx = st.selectbox("Selecione a linha pela Descrição:", options=df_mes.index, 
                             format_func=lambda x: f"{df_mes.loc[x, 'DESCRIÇÃO']} - {df_mes.loc[x, 'VALOR']}")
    
    col_ed1, col_ed2 = st.columns(2)
    with col_ed1:
        if st.button("🗑️ Excluir Linha permanentemente"):
            # O gspread usa índice 1, então somamos 2 (1 pelo cabeçalho, 1 pelo índice 0)
            sheet.delete_rows(int(linha_idx) + 2)
            st.warning("Linha excluída!")
            st.rerun()
    with col_ed2:
        novo_status = st.text_input("Mudar Status (ex: OK)", value=df_mes.loc[linha_idx, 'STATUS'])
        if st.button("💾 Salvar Alteração de Status"):
            sheet.update_cell(int(linha_idx) + 2, 3, novo_status)
            st.success("Atualizado!")
            st.rerun()
