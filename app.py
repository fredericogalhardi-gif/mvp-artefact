import streamlit as st
import json
from github import Github
from datetime import datetime
import hmac
import time
import pandas as pd
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact Strategy CRM", layout="wide", initial_sidebar_state="expanded")

# ⚠️ COLOQUE O SEU REPOSITÓRIO REAL AQUI
NOME_DO_REPOSITORIO = "fredericogalhardi-gif/mvp-artefact" 

# --- 2. LÓGICA DE TIER E LEITURA DE EXCEL ---
def calcular_tier(score):
    try:
        score = float(score)
        if score >= 48: return "Tier 1"
        elif score >= 39: return "Tier 2"
        elif score >= 20: return "Tier 3"
        else: return "Tier 4"
    except:
        return "Tier 4"

@st.cache_data
def carregar_base_de_dados():
    arquivo_excel = "base_leads.xlsx" # Nome do arquivo mudou para .xlsx
    
    if os.path.exists(arquivo_excel):
        try:
            # Lendo o Excel (ele pega a primeira aba por padrão)
            df = pd.read_excel(arquivo_excel, engine='openpyxl')
            
            # Normaliza os cabeçalhos
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            leads_processados = []
            for idx, row in df.iterrows():
                # Tratamento do Score
                try:
                    score_val = float(str(row.get('score', 0)).replace(',', '.'))
                except:
                    score_val = 0

                lead_obj = {
                    "id": f"lead_xlsx_{idx}",
                    "nome": str(row.get('nome', row.get('name', 'Nome não informado'))),
                    "empresa": str(row.get('empresa', row.get('company', 'Empresa não informada'))),
                    "cargo": str(row.get('cargo', row.get('title', 'N/I'))),
                    "decisor": str(row.get('decisor', 'N/I')),
                    "linkedin": str(row.get('linkedin', row.get('url', '#'))),
                    "score": score_val,
                    "investimentos": str(row.get('investimentos', row.get('investimento', 'N/I'))),
                    "tier": calcular_tier(score_val),
                    "outros": "Importado via Excel (.xlsx)"
                }
                leads_processados.append(lead_obj)
            return leads_processados
        except Exception as e:
            st.error(f"Erro ao ler o Excel: {e}")
            return []
    return []

# --- 3. RESTO DO CÓDIGO (LOGIN, GITHUB, UI) SEGUE O MESMO PADRÃO ANTERIOR ---
# ... (Mantenha as funções check_login, conectar_github, carregar_notas, salvar_nota e a interface que já funcionam)
