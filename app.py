import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Financeiro Barbino", layout="wide")

def conectar_google():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_info = json.loads(st.secrets["gcp_service_account"])
    else:
        with open("credentials.json") as f:
            creds_info = json.load(f)
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# --- INICIALIZAÇÃO ---
try:
    client = conectar_google()
    sheet = client.open("FINANÇAS").get_worksheet(0)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

st.title("🏠 Sistema Financeiro Barbino 2026")

# --- CARREGAR DADOS (APENAS COLUNAS A ATÉ G) ---
# Lemos apenas o intervalo que importa para evitar erro de colunas duplicadas no resto da planilha
valores = sheet.get("A1:G500") 
if valores:
    cabecalho = ["ANO", "MÊS", "STATUS", "DATA VENC", "TIPO", "VALOR", "DESCRIÇÃO"]
    # Criamos o DataFrame usando apenas os dados abaixo do cabeçalho
    df = pd.DataFrame(valores[1:], columns=cabecalho)
else:
    st.error("Não foi possível ler os dados da planilha.")
    st.stop()

# --- 1. VISUALIZAÇÃO ---
st.subheader("📊 Visualização das Colunas Principais (A-G)")
st.dataframe(df, use_container_width=True)

st.divider()

# --- 2. MENU DE OPERAÇÕES ---
operacao = st.radio("Selecione a operação:", ["Adicionar Novo Lançamento", "Editar Linha"], horizontal=True)

if operacao == "Adicionar Novo Lançamento":
    st.subheader("➕ Novo Lançamento")
    with st.form("form_novo"):
        c1, c2 = st.columns(2)
        v_ano = c1.text_input("ANO", value="2026")
        v_mes = c2.text_input("MÊS (ex: jan/26)")
        v_status = c1.selectbox("STATUS", ["", "OK", "PENDENTE"])
        v_venc = c2.text_input("DATA VENC (Dia)")
        v_tipo = c1.selectbox("TIPO", ["ENTRADA", "SAÍDA", "SALDO", "RESGATE"])
        v_valor = c2.text_input("VALOR (ex: 1500,00)")
        v_desc = st.text_input("DESCRIÇÃO DAS ENTRADAS E DESPESAS")
        
        submit = st.form_submit_button("💾 Salvar na Planilha")
        
        if submit:
            nova_linha = [v_ano, v_mes, v_status, v_venc, v_tipo, v_valor, v_desc]
            sheet.append_row(nova_linha)
            st.success("Adicionado com sucesso!")
            st.rerun()

else:
    st.subheader("📝 Editar Linha")
    idx = st.selectbox("Selecione a linha para editar:", 
                       options=df.index, 
                       format_func=lambda x: f"Linha {x+2}: {df.iloc[x]['DESCRIÇÃO']}")
    
    linha_atual = df.iloc[idx]
    
    with st.form("form_editar"):
        c1, c2 = st.columns(2)
        e_ano = c1.text_input("ANO", value=linha_atual["ANO"])
        e_mes = c2.text_input("MÊS", value=linha_atual["MÊS"])
        e_status = c1.text_input("STATUS", value=linha_atual["STATUS"])
        e_venc = c2.text_input("DATA VENC", value=linha_atual["DATA VENC"])
        e_tipo = c1.text_input("TIPO", value=linha_atual["TIPO"])
        e_valor = c2.text_input("VALOR", value=linha_atual["VALOR"])
        e_desc = st.text_input("DESCRIÇÃO", value=linha_atual["DESCRIÇÃO"])
        
        update = st.form_submit_button("✅ Atualizar Dados")
        
        if update:
            dados_atualizados = [e_ano, e_mes, e_status, e_venc, e_tipo, e_valor, e_desc]
            num_linha = int(idx) + 2
            sheet.update(f"A{num_linha}:G{num_linha}", [dados_atualizados])
            st.success(f"Linha {num_linha} atualizada!")
            st.rerun()
