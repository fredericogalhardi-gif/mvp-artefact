import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
import json
import os
import base64
from datetime import datetime

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | Strategy",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. MOTOR DE PERSISTÊNCIA FÍSICA (JSON) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, 'banco.json')
SABI_DIR = os.path.join(SCRIPT_DIR, 'sabi')

def load_notes():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_notes(notes_list):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes_list, f, ensure_ascii=False, indent=4)

# --- 3. GESTÃO DE ESTADO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'notas_locais' not in st.session_state: st.session_state.notas_locais = load_notes()

# --- 4. LÓGICA DE FOTOS DE PERFIL ---
def extract_linkedin_id(url):
    if not url or url == "#" or str(url) == 'nan': return None
    url = str(url).rstrip('/') 
    parts = url.split('/')
    return parts[-1] if parts else None

def get_photo_html(name, url, size_class="large"):
    lid = extract_linkedin_id(url)
    if lid:
        file_prefix = f"httpswww.linkedin.comin{lid}"
        valid_path = None
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG']:
            test_path = os.path.join(SABI_DIR, f"{file_prefix}{ext}")
            if os.path.exists(test_path):
                valid_path = test_path
                break
                
        if valid_path:
            try:
                with open(valid_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                mime = "image/jpeg" if valid_path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
                return f'<img src="data:{mime};base64,{b64}" class="profile-pic {size_class}">'
            except Exception: pass
    
    initials = "".join([w[0] for w in str(name).split()[:2]]).upper()
    return f'<div class="initials-placeholder {size_class}">{initials}</div>'

# --- 5. DESIGN SYSTEM & CSS ---
def apply_executive_styles():
    is_dark = st.session_state.theme == 'dark'
    C = {
        "BKG": "#050508" if is_dark else "#F4F5F7",
        "SIDEBAR": "#0A0A0F" if is_dark else "#FFFFFF",
        "TEXT": "#FFFFFF" if is_dark else "#1A1A1C",
        "SUB": "#8E8E93" if is_dark else "#636366",
        "CARD": "rgba(255, 255, 255, 0.02)" if is_dark else "#FFFFFF",
        "BORDER": "rgba(255, 255, 255, 0.08)" if is_dark else "#D1D1D6",
        "INPUT_BKG": "rgba(255, 255, 255, 0.04)" if is_dark else "#FFFFFF",
        "INPUT_TEXT": "#FFFFFF" if is_dark else "#000000",
        "BTN_SEC": "transparent" if is_dark else "#FFFFFF",
        "METRIC_BKG": "#0A0A0F" if is_dark else "#FFFFFF",
        "POT_BKG": "#030305" if is_dark else "#EAEBEE"
    }
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        .stApp {{ background-color: {C['BKG']}; font-family: 'Inter', sans-serif; color: {C['TEXT']}; }}
        [data-testid="stSidebar"] {{ background-color: {C['SIDEBAR']} !important; border-right: 1px solid {C['BORDER']}; }}
        h1, h2, h3, h4, p, span, label, li {{ color: {C['TEXT']} !important; }}
        .subtext {{ color: {C['SUB']} !important; }}
        .atf-gradient {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}
        .stTextArea textarea, .stTextInput input {{ background-color: {C['INPUT_BKG']} !important; color: {C['INPUT_TEXT']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 8px !important; }}
        button[kind="primary"] {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important; border: none !important; width: 100% !important; transition: 0.3s ease; }}
        button[kind="secondary"] {{ width: 100% !important; }}
        .profile-pic, .initials-placeholder {{ border-radius: 50%; object-fit: cover; border: 2px solid #fff; flex-shrink: 0; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .profile-pic.large, .initials-placeholder.large {{ width: 100px; height: 100px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; border-width: 1px; }}
        .initials-placeholder {{ background: linear-gradient(135deg, #3232ff, #ff1493); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; }}
        .lead-row {{ background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; position: relative; overflow: hidden; }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}
        .custom-metric-card {{ background-color: {C['METRIC_BKG']}; padding: 1.2rem; border-radius: 10px; border: 1px solid {C['BORDER']}; height: 100%; min-height: 110px; display: flex; flex-direction: column; justify-content: space-between; }}
        .metric-label {{ font-size: 0.85rem; color: {C['SUB']}; font-weight: 500; text-transform: uppercase; }}
        .metric-value {{ font-size: 1.6rem; font-weight: 700; }}
        .potencial-wrapper {{ background: {C['POT_BKG']}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1.2rem; height: 100%; display: flex; flex-direction: column; justify-content: center; }}
        .potential-value {{ font-size: 1.8rem; font-weight: 800; background: linear-gradient(90deg, #3232ff, #ff1493); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .timeline-item {{ border-left: 2px solid {C['BORDER']}; margin-left: 15px; padding-left: 20px; padding-bottom: 20px; position: relative; }}
        .timeline-item::before {{ content: ''; position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: #3232ff; }}
        div[data-testid="stHorizontalBlock"] {{ display: flex !important; flex-wrap: wrap !important; gap: 10px; }}
        [data-testid="column"] {{ flex: 1 1 calc(50% - 5px) !important; min-width: 140px !important; }}
        @media (max-width: 380px) {{ [data-testid="column"] {{ flex: 1 1 100% !important; }} }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()

# --- 6. SEGURANÇA ---
def check_login(user, pwd):
    try:
        val_u, val_p = st.secrets["APP_USER"], st.secrets["APP_PASS"]
        return hmac.compare_digest(user.encode('utf-8'), val_u.encode('utf-8')) and hmac.compare_digest(pwd.encode('utf-8'), val_p.encode('utf-8'))
    except: return False

if not st.session_state.logado:
    st.write("\n" * 4)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<h1 class="atf-gradient" style="font-size:3rem; text-align:center;">Artefact</h1>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Corporate ID")
            p = st.text_input("Security Token", type="password")
            if st.form_submit_button("Authenticate", type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Access Denied.")
    st.stop()

# --- 7. DATA ENGINE REAL (BASEADO NO CSV) ---
LEADS_BASE = [
    {
        "id": 17,
        "nome": "Camila Alves Massaro",
        "empresa": "ArcelorMittal Gonvarri",
        "cargo": "Director of People, Strategy & IT",
        "decisor": "Sim",
        "score": 58,
        "linkedin": "https://www.linkedin.com/in/camilamassaro-rh",
        "bio": "Processamento e distribuição de aço.",
        "interesse": "Novos Modelos de Trabalho, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "orcamento_real": "De 50 milhões até 100 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 500 a 1000 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "Gestão de Mudança e Cultura Organizacional",
        "comentarios_caio": "Temos contato, fizemos várias propostas negadas mas nunca foi vendido. quem tem contato lá é o victor pontello"
    },
    {
        "id": 1,
        "nome": "Bruno Szarf",
        "empresa": "Stefanini",
        "cargo": "VP Global",
        "decisor": "Sim",
        "score": 56,
        "linkedin": "https://www.linkedin.com/in/brunoszarf",
        "bio": "Consultoria e soluções em TI.",
        "interesse": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Cultura Organizacional",
        "desafios": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados",
        "orcamento_real": "De 10 milhões até 50 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "4 - 6 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 2,
        "nome": "Brenda Donato Endo",
        "empresa": "Embracon",
        "cargo": "Diretora de RH",
        "decisor": "Sim",
        "score": 56,
        "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041",
        "bio": "Administradora de consórcios de bens.",
        "interesse": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Cultura Organizacional, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "desafios": "Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Diversidade, Equidade e Inclusão (DE&I), Alinhamento Estratégico com a Alta Direção, Sustentabilidade e ESG no RH",
        "orcamento_real": "De 10 milhões até 50 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 3,
        "nome": "Soraya Bahde",
        "empresa": "Bradesco",
        "cargo": "Diretora",
        "decisor": "Não",
        "score": 54,
        "linkedin": "https://www.linkedin.com/in/sorayabahde",
        "bio": "Serviços bancários e financeiros completos.",
        "interesse": "Treinamento e Desenvolvimento, Gestão da Mudança, Cultura Organizacional, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "desafios": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "orcamento_real": "Acima de 100 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "Mais 18 meses",
        "solucao": "Treinamento e desenvolvimento",
        "comentarios_caio": "A finor conhece o pessoal de lá, acho que é o Tiago. é um cliente atual"
    },
    {
        "id": 10,
        "nome": "Patrícia Rosado",
        "empresa": "Tupy",
        "cargo": "VP de Pessoas, Cultura e SSMA",
        "decisor": "Sim",
        "score": 54,
        "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a",
        "bio": "Metalúrgica e fundição de componentes.",
        "interesse": "Treinamento e Desenvolvimento, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional",
        "desafios": "Gestão da Cultura Híbrida, Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "4 - 6 meses",
        "solucao": "Nada específico, quero conhecer o que tiver relacionado",
        "comentarios_caio": ""
    },
    {
        "id": 12,
        "nome": "RITA SOUZA",
        "empresa": "Bunge Alimentos",
        "cargo": "Diretora Gestão Mudança Organizacional",
        "decisor": "Sim",
        "score": 54,
        "linkedin": "https://www.linkedin.com/in/rita-souza-neurochange/",
        "bio": "Processamento de grãos e óleos.",
        "interesse": "Gestão da Mudança, Cultura Organizacional",
        "desafios": "Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "7 - 12 meses",
        "solucao": "Adoção IA",
        "comentarios_caio": "É cliente atual. Quem lidera a conta é o Mauricio e o Lourenço. Principal buyer é o Felipe Miana"
    },
    {
        "id": 6,
        "nome": "Patricia Bobbato",
        "empresa": "Natura",
        "cargo": "Diretora de Cultura, Desenvolvimento, Bem estar e DE&I",
        "decisor": "Sim",
        "score": 52,
        "linkedin": "https://www.linkedin.com/in/patriciabobbato",
        "bio": "Cosméticos e produtos de higiene.",
        "interesse": "Novos Modelos de Trabalho, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "desafios": "Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "7 - 12 meses",
        "solucao": "EVP é Skill based",
        "comentarios_caio": "Acho que tamo fazendo proposta lá. Quem tá liderando é o Mauricio aparentemente, mas acho que o Selli tem contexto. não é cliente, apenas lead"
    },
    {
        "id": 9,
        "nome": "Alisson Gratão",
        "empresa": "Copagril",
        "cargo": "Superintendente de Gestão de Pessoas",
        "decisor": "Sim",
        "score": 52,
        "linkedin": "https://www.linkedin.com/in/alisson1",
        "bio": "Cooperativa agroindustrial de produção diversa.",
        "interesse": "Aquisição e Retenção de Talentos, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "desafios": "Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": ".",
        "comentarios_caio": ""
    },
    {
        "id": 27,
        "nome": "Daniela Monteiro",
        "empresa": "Editora do Brasil",
        "cargo": "Diretora de RH & Marca",
        "decisor": "Sim",
        "score": 49,
        "linkedin": "https://br.linkedin.com/in/daniela-monteiro-a3125970",
        "bio": "Educação médica e tecnologias digitais.",
        "interesse": "Automação de Processos no RH",
        "desafios": "Adoção e Integração de IA/Automação",
        "orcamento_real": "De 50 milhões até 100 milhões",
        "receita": "De 250 milhoes até 500 milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "-",
        "comentarios_caio": "Tamo tentando vender um projeto de agentes lá. Quem tem contato é o Selli"
    },
    {
        "id": 16,
        "nome": "Neto Mello",
        "empresa": "Adimax",
        "cargo": "Diretor de RH / CHRO",
        "decisor": "Não",
        "score": 48,
        "linkedin": "https://www.linkedin.com/in/netomello",
        "bio": "Fabricação de alimentos para pets.",
        "interesse": "Treinamento e Desenvolvimento, Recrutamento e Seleção, Cultura Organizacional",
        "desafios": "Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, Gestão de Mudança Organizacional",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Liderança e Cultura",
        "comentarios_caio": ""
    },
    {
        "id": 18,
        "nome": "Willian Souza",
        "empresa": "EMS",
        "cargo": "Diretor de Governança e Treinamento",
        "decisor": "Não",
        "score": 48,
        "linkedin": "https://www.linkedin.com/in/willian-souza-63874147",
        "bio": "Indústria farmacêutica e medicamentos genéricos.",
        "interesse": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Gestão da Mudança",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "4 - 6 meses",
        "solucao": "Treinamento e tomada de decisão apoiada por dados",
        "comentarios_caio": ""
    },
    {
        "id": 33,
        "nome": "Diná Ribeiro de Carvalho",
        "empresa": "Superlógica",
        "cargo": "Diretora de Gente e Gestão",
        "decisor": "Sim",
        "score": 48,
        "linkedin": "https://br.linkedin.com/in/din%C3%A1-ribeiro-de-carvalho-a1a184348",
        "bio": "indefinido",
        "interesse": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Aquisição e Retenção de Talentos, Saúde Corporativa e Bem Estar",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Adoção e Integração de IA/Automação",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "De 500 milhoes até 750 milhoes",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "4 - 6 meses",
        "solucao": "Saúde Mental / IA para G&G",
        "comentarios_caio": ""
    },
    {
        "id": 4,
        "nome": "Ana Luiza Guimarães Brasil",
        "empresa": "Fortbras",
        "cargo": "Diretor de Gente e Gestão",
        "decisor": "Não",
        "score": 46,
        "linkedin": "https://www.linkedin.com/in/brasilana",
        "bio": "Distribuição de autopeças e serviços.",
        "interesse": "Automação de Processos no RH",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 5000 a 10000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "neste momento não tenho nenhuma",
        "comentarios_caio": ""
    },
    {
        "id": 11,
        "nome": "Danila Pires Carsoso",
        "empresa": "Motiva",
        "cargo": "Diretor",
        "decisor": "Não",
        "score": 46,
        "linkedin": "#",
        "bio": "Soluções de atendimento e telemarketing.",
        "interesse": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Cultura Organizacional",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "4 - 6 meses",
        "solucao": "Aquisição e retenção de talentos",
        "comentarios_caio": ""
    },
    {
        "id": 14,
        "nome": "Gerson Cosme santos",
        "empresa": "GHT",
        "cargo": "Diretor gente & performance",
        "decisor": "Não",
        "score": 46,
        "linkedin": "https://www.linkedin.com/in/gerson-cosme-santos",
        "bio": "Peças para máquinas pesadas (mineração).",
        "interesse": "Automação de Processos no RH",
        "desafios": "Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 500 a 1000 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "Automação",
        "comentarios_caio": ""
    },
    {
        "id": 30,
        "nome": "Frederico Consetino Neto",
        "empresa": "Afya",
        "cargo": "Diretor de Recursos Humanos",
        "decisor": "Não",
        "score": 46,
        "linkedin": "https://www.linkedin.com/in/frederico-cosentino-b67b1a20",
        "bio": "Software de gestão para condomínios.",
        "interesse": "Benefícios Flexíveis, Saúde Corporativa e Bem Estar",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, Cibersegurança e Privacidade de Dados, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Construção de uma Proposta de Valor ao Empregado (EVP) Forte, Sustentabilidade e ESG no RH",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 5000 a 10000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Adoção e Integração de IA/Automação",
        "comentarios_caio": "Contato antigo, que morreu faz tempo. acho que não temos mais contato hoje"
    },
    {
        "id": 22,
        "nome": "Angelo Fanti",
        "empresa": "Sorocaba Refrescos S/A",
        "cargo": "Diretor Recursos Humanos",
        "decisor": "Sim",
        "score": 43,
        "linkedin": "https://br.linkedin.com/in/angelo-fanti-58a4a821",
        "bio": "Aluguel de equipamentos para construção.",
        "interesse": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "orcamento_real": "abaixo de 1 milhão",
        "receita": "De 250 milhoes até 500 milhoes",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Impactos da IA na cultura organizacional",
        "comentarios_caio": ""
    },
    {
        "id": 32,
        "nome": "Mari Stela Ribeiro",
        "empresa": "HILTI do Brasil",
        "cargo": "CHRO",
        "decisor": "Não",
        "score": 43,
        "linkedin": "https://www.linkedin.com/in/mariribeiro",
        "bio": "Rede varejista de alimentos.",
        "interesse": "Treinamento e Desenvolvimento, Automação de Processos no RH, Saúde Corporativa e Bem Estar",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "De 750 milhoes até 1bilhao",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "nenhuma em especifico",
        "comentarios_caio": ""
    },
    {
        "id": 7,
        "nome": "Juliana Dorigo",
        "empresa": "Grupo Ecoagro",
        "cargo": "Diretora de RH",
        "decisor": "Sim",
        "score": 40,
        "linkedin": "https://www.linkedin.com/in/julianadorigorh",
        "bio": "Consultoria e estruturação de agronegócio.",
        "interesse": "Cultura Organizacional, Gestão de Desempenho e Talentos",
        "desafios": "Sustentabilidade e ESG no RH",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "Alinhamento Estratégico com a Alta Direção",
        "comentarios_caio": ""
    },
    {
        "id": 25,
        "nome": "Thais Cristina de Abreu Vendramini Ferreira",
        "empresa": "G5 Partners",
        "cargo": "Vice President - People and Culture Manager",
        "decisor": "Sim",
        "score": 40,
        "linkedin": "https://www.linkedin.com/in/thais-vendramini/",
        "bio": "Publicação de livros didáticos e literários.",
        "interesse": "Treinamento e Desenvolvimento, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional, Software de Gestão para RH",
        "desafios": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Gostaria de entender melhor temas e possibilidades de como aplicar e ficar mais próximo dos exceutivos e decisores",
        "comentarios_caio": ""
    },
    {
        "id": 31,
        "nome": "Tâmara Costa",
        "empresa": "SantoDigital",
        "cargo": "Diretora de RH",
        "decisor": "Não",
        "score": 40,
        "linkedin": "https://www.linkedin.com/in/tamiscosta",
        "bio": "Produção de laticínios e derivados.",
        "interesse": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Recrutamento e Seleção, Cultura Organizacional",
        "desafios": "Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "De 500 milhoes até 750 milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "4 - 6 meses",
        "solucao": "Desenvolvimento de líderes, automação para RH",
        "comentarios_caio": ""
    },
    {
        "id": 29,
        "nome": "Mario Felicio Neto",
        "empresa": "CPQD",
        "cargo": "Diretor de Gente e gestão",
        "decisor": "Não",
        "score": 39,
        "linkedin": "https://www.linkedin.com/in/mario-felicio-neto",
        "bio": "Ferramentas profissionais para construção civil.",
        "interesse": "Benefícios Flexíveis, Treinamento e Desenvolvimento, Diversidade e Inclusão",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças,",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "De 250 milhoes até 500 milhoes",
        "funcionarios": "De 500 a 1000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Todas",
        "comentarios_caio": ""
    },
    {
        "id": 13,
        "nome": "GIOVANI CARRA",
        "empresa": "ADF ONDULADOS E LOGISTICA",
        "cargo": "DIRETOR DE RH",
        "decisor": "Não",
        "score": 34,
        "linkedin": "https://www.linkedin.com/in/giovani-carra-65858a33",
        "bio": "Embalagens de papelão e logística.",
        "interesse": "Treinamento e Desenvolvimento, Cultura Organizacional",
        "desafios": "Desenvolvimento de Lideranças, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "ALINHAMENTO ESTRATEGICO",
        "comentarios_caio": "Sem foto"
    },
    {
        "id": 19,
        "nome": "Aldo Silva dos Santos",
        "empresa": "HCOSTA",
        "cargo": "CHRO Gente e Gestão",
        "decisor": "Não",
        "score": 34,
        "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/",
        "bio": "Escritório de advocacia e cobrança.",
        "interesse": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional, Software de Gestão para RH",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "Saude Metal (NR1), DHO, Sistemas de Gestão RH",
        "comentarios_caio": ""
    },
    {
        "id": 36,
        "nome": "Caroline Faki de Miranda",
        "empresa": "Vigor Alimentos",
        "cargo": "Head de Business Partner",
        "decisor": "Não",
        "score": 34,
        "linkedin": "https://www.linkedin.com/in/caroline-faki-68338285",
        "bio": "Greenbrier – construção e leasing de vagões de carga; Maxion – fabricação de rodas para veículos",
        "interesse": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Aquisição e Retenção de Talentos, Cultura Organizacional, Software de Gestão para RH",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Sobre de IA",
        "comentarios_caio": ""
    },
    {
        "id": 37,
        "nome": "Marcelo Carlos Pinheiro",
        "empresa": "Greenbrier Maxion",
        "cargo": "Gerente Senior",
        "decisor": "Não",
        "score": 30,
        "linkedin": "https://www.linkedin.com/in/marcelo-pinheiro-274abb24",
        "bio": "fabricação e reforma de vagões de carga",
        "interesse": "Treinamento e Desenvolvimento",
        "desafios": "Alinhamento Estratégico com a Alta Direção",
        "orcamento_real": "De 10 milhões até 50 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 500 a 1000 funcionários",
        "prazo": "4 - 6 meses",
        "solucao": "Inovação",
        "comentarios_caio": ""
    },
    {
        "id": 38,
        "nome": "Jader Eder Bleil",
        "empresa": "Greenbrier Maxion Equipamentos e Serviços Ferroviários S/A",
        "cargo": "Gerente RT",
        "decisor": "Não",
        "score": 30,
        "linkedin": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225",
        "bio": "indefinido",
        "interesse": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Gestão da Mudança, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "desafios": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "orcamento_real": "De 10 milhões até 50 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 500 a 1000 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 8,
        "nome": "Daniela Nishimoto",
        "empresa": "Grupo L'Oréal",
        "cargo": "Diretora/ Executiva de Relações Humanas",
        "decisor": "Não",
        "score": 29,
        "linkedin": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1",
        "bio": "Fabricação global de produtos cosméticos.",
        "interesse": "N/I",
        "desafios": "N/I",
        "orcamento_real": "N/I",
        "receita": "Outro",
        "funcionarios": "Acima de 10000",
        "prazo": "N/I",
        "solucao": "N/I",
        "comentarios_caio": ""
    },
    {
        "id": 15,
        "nome": "Lenita David Gilioli Pedreira de Freitas",
        "empresa": "Flora Produtos",
        "cargo": "Gerente executiva de RH",
        "decisor": "Não",
        "score": 28,
        "linkedin": "https://www.linkedin.com/in/lenita-gilioli-freitas",
        "bio": "Cosméticos e limpeza doméstica (Minuano).",
        "interesse": "Treinamento e Desenvolvimento, Automação de Processos no RH, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "desafios": "Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 20,
        "nome": "Daniel Peruchi",
        "empresa": "Alcoa",
        "cargo": "Gerente Sênior RH",
        "decisor": "Não",
        "score": 25,
        "linkedin": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9",
        "bio": "Produção e processamento de alumínio.",
        "interesse": "Benefícios Flexíveis, Treinamento e Desenvolvimento, Novos Modelos de Trabalho",
        "desafios": "Desenvolvimento de Lideranças, Atualização Constante de Habilidades (Skills Gap)",
        "orcamento_real": "N/I",
        "receita": "De 500 milhoes até 750 milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 26,
        "nome": "Thamires C. Alves Pedro Justino",
        "empresa": "Alcoa Alumínio S/A",
        "cargo": "Gerente de RH",
        "decisor": "Não",
        "score": 24,
        "linkedin": "https://www.linkedin.com/in/thamires-pedro-15287611b/",
        "bio": "Soluções corporativas e serviços.",
        "interesse": "Aquisição e Retenção de Talentos, Gestão da Mudança, Cultura Organizacional",
        "desafios": "Desenvolvimento de Lideranças, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Acima de 10000",
        "prazo": "13 - 18 meses",
        "solucao": "Engajamento",
        "comentarios_caio": ""
    },
    {
        "id": 28,
        "nome": "Ariana Tertuliano",
        "empresa": "Casa do Construtor",
        "cargo": "Gerente de RH",
        "decisor": "Não",
        "score": 23,
        "linkedin": "https://www.linkedin.com/in/ariana-tertuliano-81a65538",
        "bio": "Criação e comercialização de conteúdo.",
        "interesse": "Cultura Organizacional",
        "desafios": "Gestão de Mudança Organizacional",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Abaixo de 250milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "Atração e retenção",
        "comentarios_caio": ""
    },
    {
        "id": 21,
        "nome": "Ricardo Malvestite",
        "empresa": "GBMX",
        "cargo": "Gerente Sr RH",
        "decisor": "Não",
        "score": 22,
        "linkedin": "https://www.linkedin.com/in/ricardo-malvestite-74b1936",
        "bio": "Produção de alumínio.",
        "interesse": "Automação de Processos no RH",
        "desafios": "Adoção e Integração de IA/Automação",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 23,
        "nome": "Sabrina G. Rosa Lemes",
        "empresa": "GBMX",
        "cargo": "Gerente EHS",
        "decisor": "Não",
        "score": 21,
        "linkedin": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107",
        "bio": "Equipamentos ferroviários.",
        "interesse": "Automação de Processos no RH, Cultura Organizacional",
        "desafios": "Gestão de Mudança Organizacional",
        "orcamento_real": "De 2 milhões até 10 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "4 - 6 meses",
        "solucao": "-",
        "comentarios_caio": ""
    },
    {
        "id": 35,
        "nome": "ANDRE L E ARANHA",
        "empresa": "SUPERLOGICA",
        "cargo": "GERENTE DE REMUNERAÇÃO, DESEMPENHO E BENEFICIOS",
        "decisor": "Não",
        "score": 19,
        "linkedin": "https://www.linkedin.com/in/andrelearanha",
        "bio": "Franquias de locação de equipamentos.",
        "interesse": "Benefícios Flexíveis, Treinamento e Desenvolvimento, Gestão da Mudança, Cultura Organizacional",
        "desafios": "Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Gestão de Mudança Organizacional",
        "orcamento_real": "De 50 milhões até 100 milhões",
        "receita": "De 500 milhoes até 750 milhoes",
        "funcionarios": "Abaixo de 500 funcionários",
        "prazo": "0 - 3 meses",
        "solucao": "Engajamento",
        "comentarios_caio": ""
    },
    {
        "id": 34,
        "nome": "Nelson Simeoni Junior",
        "empresa": "Superlógica",
        "cargo": "Gerente de DHO",
        "decisor": "Não",
        "score": 18,
        "linkedin": "https://www.linkedin.com/in/nelsonsimeoni",
        "bio": "indefinido",
        "interesse": "Treinamento e Desenvolvimento, Cultura Organizacional",
        "desafios": "Desenvolvimento de Lideranças, Atualização Constante de Habilidades (Skills Gap)",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "De 500 milhoes até 750 milhoes",
        "funcionarios": "De 1000 a 5000 funcionários",
        "prazo": "7 - 12 meses",
        "solucao": "Liderança",
        "comentarios_caio": ""
    },
    {
        "id": 24,
        "nome": "Michele Ferreira",
        "empresa": "Confiança Supermercados",
        "cargo": "Coordenadora de DHO",
        "decisor": "Não",
        "score": 14,
        "linkedin": "https://www.linkedin.com/in/michele-ferreira-16401083",
        "bio": "Laticínios e produtos alimentícios.",
        "interesse": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Cultura Organizacional",
        "desafios": "Desenvolvimento de Lideranças",
        "orcamento_real": "Abaixo de 2 milhões",
        "receita": "Acima de 1bilhao",
        "funcionarios": "De 5000 a 10000 funcionários",
        "prazo": "13 - 18 meses",
        "solucao": "Gestão da Mudança",
        "comentarios_caio": ""
    }
]

def calc_meta(score):
    if score >= 48: return "Tier 1", "> R$ 1 Milhão", "pill-blue"
    if score >= 39: return "Tier 2", "R$ 500k - 1M", "pill-magenta"
    return "Tier 3", "< R$ 500k", "pill-neutral"

for l in LEADS_BASE:
    l['t'], l['o'], l['c'] = calc_meta(l['score'])

df_leads = pd.DataFrame(LEADS_BASE)

# --- 8. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient" style="margin-bottom: 2rem;">Artefact</h2>', unsafe_allow_html=True)
    if st.button("📊 Executive Dash", use_container_width=True, disabled=(st.session_state.view_mode=='dashboard')): st.session_state.view_mode='dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=(st.session_state.view_mode=='list')): st.session_state.view_mode='list'; st.rerun()
    st.divider()
    if st.button("🌓 Toggle Theme", use_container_width=True): st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()
    if st.button("🚪 Logout", use_container_width=True): st.session_state.logado = False; st.rerun()

# --- 9. VIEWS ---
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1>Executive Overview</h1>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="custom-metric-card"><p class="metric-label">Contas Mapeadas</p><p class="metric-value">{len(df_leads)}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisores Confirmados</p><p class="metric-value">{len(df_leads[df_leads["decisor"] == "Sim"])}</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="potencial-wrapper"><span class="metric-label">Volume Pipeline</span><p class="potential-value">> R$ 25.5M</p></div>', unsafe_allow_html=True)
    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### Pipeline Health")
        fig_bar = px.bar(df_leads.sort_values('score').tail(10), x='score', y='nome', orientation='h', color='t', color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#8E8E93", height=300, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    with g2:
        st.markdown("### Distribuição Estratégica")
        fig_donut = px.pie(df_leads, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_donut.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#8E8E93", height=300, showlegend=False)
        st.plotly_chart(fig_donut, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filtrar", ["Todos", "Tier 1", "Tier 2", "Tier 3"], label_visibility="collapsed")
    f_leads = LEADS_BASE if sel == "Todos" else [l for l in LEADS_BASE if sel in l['t']]
    for l in f_leads:
        bar = '<div class="tier-1-bar"></div>' if "Tier 1" in l['t'] else ""
        photo_html = get_photo_html(l['nome'], l.get('linkedin', '#'), "small")
        card = f"""<div class="lead-row">{bar}<div style="display:flex; align-items:center; gap:15px; margin-bottom:12px;">{photo_html}<div style="flex:1;"><strong style="font-size:1.15rem;">{l['nome']}</strong><br><span class="subtext">{l['cargo']}</span></div><div style="text-align:right;"><span class="{l['c']}">{l['t']}</span></div></div><div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid rgba(128,128,128,0.2);"><span style="font-weight:600;">{l['empresa']}</span><span class="{l['c']}">{l['o']}</span></div></div>"""
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Analisar Perfil", key=f"b_{l['id']}", use_container_width=True): st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Pipeline", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    st.write("")
    photo_html = get_photo_html(l['nome'], l.get('linkedin', '#'), "large")
    st.markdown(f'<div style="display:flex; align-items:center; gap:20px; margin-bottom:20px; flex-wrap:wrap;">{photo_html}<div><h1 style="margin-bottom:0; font-size:2.2rem;">{l["nome"]}</h1><p class="subtext" style="font-size:1.1rem; margin-top:5px;">{l["cargo"]} @ <strong>{l["empresa"]}</strong></p></div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Classificação</p><p class="metric-value">{l["t"]}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Score</p><p class="metric-value">{l["score"]} pts</p></div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisor</p><p class="metric-value">{l["decisor"]}</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="potencial-wrapper"><p class="metric-label">Potencial</p><p class="potential-value">{l["o"]}</p></div>', unsafe_allow_html=True)
    
    with st.expander("📂 Visualizar Dossiê Completo"):
        e1, e2 = st.columns(2)
        e1.markdown(f"**🏢 Receita:** {l['receita']}\n\n**👥 Funcionários:** {l['funcionarios']}\n\n**🎯 Desafios:** {l['desafios']}")
        e2.markdown(f"**⏳ Prazo Investimento:** {l['prazo']}\n\n**🛠 Solução Desejada:** {l['solucao']}\n\n**💡 Comentários:** {l['comentarios_caio']}")
        if l.get('linkedin') and l['linkedin'] != "#": st.link_button("Abrir LinkedIn", l['linkedin'])

    st.divider()
    st.markdown("### Registro")
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota", placeholder="Insights da interação...", label_visibility="collapsed")
        audio_val = st.audio_input("Gravar Voice Note (Opcional)") if hasattr(st, 'audio_input') else None
        if st.form_submit_button("Salvar Registro", type="primary"):
            audio_b64 = base64.b64encode(audio_val.read()).decode() if audio_val else None
            st.session_state.notas_locais.insert(0, {"id_lead": l['id'], "dt": datetime.now().strftime("%d/%m/%Y %H:%M"), "txt": txt.strip(), "audio": audio_b64})
            save_notes(st.session_state.notas_locais); st.rerun()
    for n in [x for x in st.session_state.notas_locais if x.get('id_lead') == l['id']]:
        audio_html = f'<audio controls src="data:audio/wav;base64,{n["audio"]}"></audio>' if n.get('audio') else ""
        st.markdown(f'<div class="timeline-item"><p class="timeline-date">{n["dt"]}</p><p class="timeline-note">{n["txt"]}</p>{audio_html}</div>', unsafe_allow_html=True)
