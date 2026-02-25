import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Finanças 2026", layout="wide")

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
    # Abre a planilha pelo nome exato que está no teu Drive
    sheet = client.open("FINANÇAS").get_worksheet(0)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

st.title("🏠 Sistema Financeiro Barbino 2026")

# --- CARREGAR DADOS ---
# Forçamos a leitura para garantir que temos os dados mais frescos
dados = sheet.get_all_values()
df = pd.DataFrame(dados[1:], columns=dados[0])

# --- 1. VISUALIZAÇÃO ---
st.subheader("📊 Visualização Atual (Planilha)")
st.dataframe(df, use_container_width=True)

st.divider()

# --- 2. MENU DE OPERAÇÕES ---
aba_escolhida = st.radio("O que deseja fazer?", ["Editar Linha Existente", "Adicionar Novo Lançamento"], horizontal=True)

# Lista das 7 colunas principais (A até G) baseada na tua imagem
colunas_principais = ["ANO", "MÊS", "STATUS", "DATA VENC", "TIPO", "VALOR", "DESCRIÇÃO"]

if aba_escolhida == "Editar Linha Existente":
    st.subheader("📝 Editar Lançamento")
    linha_selecionada = st.selectbox("Selecione a linha para editar:", 
                                     options=df.index, 
                                     format_func=lambda x: f"Linha {x + 2} - {df.iloc[x]['DESCRIÇÃO']}")
    
    valores_atuais = df.iloc[linha_selecionada]
    
    with st.form("form_editar"):
        novos_dados = []
        c1, c2 = st.columns(2)
        for i, col_nome in enumerate(colunas_principais):
            # Usamos uma chave (key) única para evitar o erro de DuplicateElementId
            with c1 if i % 2 == 0 else c2:
                # Preenchemos com o valor que já existe na planilha
                valor_original = valores_atuais[i] if i < len(valores_atuais) else ""
                val = st.text_input(f"{col_nome}", value=valor_original, key=f"edit_{i}")
                novos_dados.append(val)
        
        btn_editar = st.form_submit_button("✅ Atualizar na Planilha")
        
        if btn_editar:
            num_linha = int(linha_selecionada) + 2
            sheet.update(f"A{num_linha}:G{num_linha}", [novos_dados])
            st.success(f"Linha {num_linha} atualizada!")
            st.rerun()

else:
    st.subheader("➕ Novo Lançamento")
    with st.form("form_novo"):
        novos_dados = []
        c1, c2 = st.columns(2)
        for i, col_nome in enumerate(colunas_principais):
            with c1 if i % 2 == 0 else c2:
                # Sugestão de valores padrão para facilitar
                valor_padrao = "2026" if col_nome == "ANO" else ""
                val = st.text_input(f"{col_nome}", value=valor_padrao, key=f"novo_{i}")
                novos_dados.append(val)
        
        btn_salvar = st.form_submit_button("💾 Salvar Novo Lançamento")
        
        if btn_salvar:
            sheet.append_row(novos_dados)
            st.success("Novo lançamento adicionado com sucesso!")
            st.rerun()
