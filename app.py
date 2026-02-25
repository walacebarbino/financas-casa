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
    # Abrindo a primeira aba disponível para evitar erro de nome
    sheet = client.open("FINANÇAS").get_worksheet(0)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

st.title("🏠 Gestão Finanças 2026")

# --- VISUALIZAÇÃO DA PLANILHA ---
st.subheader("📊 Visualização da Planilha")
dados = sheet.get_all_values()
if dados:
    # Criamos o DataFrame
    df = pd.DataFrame(dados[1:], columns=dados[0])
    # Exibe a planilha na tela
    st.dataframe(df, use_container_width=True)
else:
    st.warning("A planilha parece estar vazia.")
    st.stop()

st.divider()

# --- ÁREA DE EDIÇÃO ---
st.subheader("📝 Editar Lançamentos")
linha_idx = st.selectbox("Selecione o número da linha para editar (veja na tabela acima):", 
                         options=df.index, 
                         format_func=lambda x: f"Linha {x + 2}")

valores_atuais = df.iloc[linha_idx]

# Formulário de edição
with st.form("meu_formulario"):
    st.write(f"Alterando dados da Linha {linha_idx + 2}")
    
    novos_valores = []
    # Criamos 7 campos de edição (Colunas A até G)
    cols = st.columns(4)
    
    for i in range(7):
        nome_coluna = df.columns[i] if i < len(df.columns) else f"Coluna {i}"
        # Se o nome da coluna for vazio ou repetido, o 'key' evita o erro DuplicateElementId
        with cols[i % 4]:
            novo_val = st.text_input(f"{nome_coluna}", 
                                     value=valores_atuais[i], 
                                     key=f"input_{i}_{linha_idx}")
            novos_valores.append(novo_val)
    
    # O BOTÃO DEVE ESTAR DENTRO DO FORMULÁRIO
    botao_salvar = st.form_submit_button("💾 Salvar Alterações na Nuvem")

if botao_salvar:
    try:
        # Define o intervalo de A até G para a linha selecionada
        num_linha_real = int(linha_idx) + 2
        intervalo = f"A{num_linha_real}:G{num_linha_real}"
        
        sheet.update(intervalo, [novos_valores])
        st.success(f"Linha {num_linha_real} atualizada com sucesso!")
        st.rerun() # Atualiza a visualização
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
