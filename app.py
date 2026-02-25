import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- CONFIGURAÇÃO DA CONEXÃO ---
def conectar_google():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Se estiver no Streamlit Cloud, usa os Secrets. Se estiver local, usa o ficheiro JSON.
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
    # Abre a planilha pelo nome exato
    sheet = client.open("FINANÇAS").worksheet("FINANÇAS")
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

st.title("🏠 Gestão Finanças 2026")

# --- CARREGAR DADOS ---
dados = sheet.get_all_values()
df = pd.DataFrame(dados[1:], columns=dados[0])

# --- EDIÇÃO DAS COLUNAS A-G ---
st.subheader("📝 Editar Lançamentos")
linha_idx = st.selectbox("Selecione a linha:", df.index)
valores = df.iloc[linha_idx]

with st.form("edit_form"):
    # Criamos inputs apenas para as 7 primeiras colunas (A a G)
    novos_valores = []
    cols = st.columns(4)
    for i in range(7):
        with cols[i % 4]:
            val = st.text_input(f"{df.columns[i]}", valores[i])
            novos_valores.append(val)
    
    enviar = st.form_submit_button("Atualizar na Nuvem")

if enviar:
    # O Excel começa na linha 1 e tem cabeçalho, então linha_idx + 2
    row_num = int(linha_idx) + 2
    sheet.update(f"A{row_num}:G{row_num}", [novos_valores])
    st.success("Dados atualizados! As fórmulas do Excel farão o resto.")
    st.rerun()

# --- EXIBIÇÃO ---
st.divider()
st.dataframe(df)
