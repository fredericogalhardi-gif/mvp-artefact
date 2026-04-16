import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
import os
import base64
import re
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | Strategy",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SUPABASE CONNECTION (DATABASE & STORAGE) ---
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Erro Crítico: Credenciais do Supabase não encontradas nos Secrets.")
        st.stop()
    except Exception as e:
        st.error(f"Falha ao inicializar Supabase: {e}")
        st.stop()

supabase = get_supabase_client()

def load_notes_from_supabase(lead_id: str):
    try:
        response = supabase.table("notas").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao carregar notas: {e}")
        return []

def save_note_to_supabase(lead_id: str, texto: str, audio_url: str = None):
    try:
        data = {
            "lead_id": str(lead_id),
            "texto": texto,
            "created_at": datetime.now().isoformat()
        }
        if audio_url:
            data["audio_url"] = audio_url
            
        supabase.table("notas").insert(data).execute()
    except Exception as e:
        st.error(f"Erro ao salvar nota: {e}")

def upload_audio_to_supabase(audio_bytes, lead_id: str):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_lead_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))
        filename = f"registro_{safe_lead_id}_{timestamp}.wav"
        
        supabase.storage.from_("gravacoes").upload(
            file=audio_bytes,
            path=filename,
            file_options={"content-type": "audio/wav"}
        )
        url = supabase.storage.from_("gravacoes").get_public_url(filename)
        return url
    except Exception as e:
        st.error(f"Erro no upload de áudio: {e}")
        return None

# --- 3. GESTÃO DE ESTADO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'

# --- 4. LÓGICA DE FOTOS DE PERFIL (/sabi) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SABI_DIR = os.path.join(SCRIPT_DIR, 'sabi')

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

# --- 5. DESIGN SYSTEM & CSS (LIQUID RESPONSIVENESS) ---
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

        .atf-gradient {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        .stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {{
            background-color: {C['INPUT_BKG']} !important; color: {C['INPUT_TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; border-radius: 8px !important;
            caret-color: #3232ff !important; padding: 14px !important; width: 100% !important;
            box-sizing: border-box !important; font-size: 0.95rem !important;
        }}
        div[data-baseweb="textarea"], div[data-baseweb="input"] {{ background-color: transparent !important; border: none !important; }}
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.6 !important; }}

        button[kind="secondary"], .stLinkButton > a {{
            background-color: {C['BTN_SEC']} !important; color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; border-radius: 8px !important;
            transition: all 0.2s ease !important; width: 100% !important; 
            display: inline-flex; align-items: center; justify-content: center; font-weight: 500 !important;
        }}
        button[kind="secondary"]:hover, .stLinkButton > a:hover {{ border-color: #3232ff !important; background-color: rgba(50, 50, 255, 0.05) !important; }}

        button[kind="primary"] {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important;
            border: none !important; border-radius: 8px !important; width: 100% !important; 
            font-weight: 600 !important; transition: all 0.3s ease !important;
        }}
        button[kind="primary"]:hover {{ transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(50, 50, 255, 0.4) !important; }}

        .profile-pic, .initials-placeholder {{
            border-radius: 50%; object-fit: cover; border: 2px solid #fff;
            flex-shrink: 0; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        .profile-pic.large, .initials-placeholder.large {{ width: 100px; height: 100px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; border-width: 1px; }}
        .initials-placeholder {{
            background: linear-gradient(135deg, #3232ff, #ff1493);
            color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800;
        }}
        .initials-placeholder.large {{ font-size: 2.2rem; }}
        .initials-placeholder.small {{ font-size: 1.2rem; }}

        .lead-row {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px;
            padding: 1.2rem; margin-bottom: 1rem; position: relative; overflow: hidden; transition: all 0.2s ease;
        }}
        .lead-row:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.05); }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}

        div[data-testid="stMetric"] {{
            background: {C['METRIC_BKG']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1.2rem !important; height: 100%;
        }}
        div[data-testid="stHorizontalBlock"] {{
            display: flex !important; flex-wrap: wrap !important; gap: 1rem !important; width: 100% !important;
        }}
        [data-testid="column"] {{
            flex: 1 1 40% !important; min-width: 140px !important; box-sizing: border-box !important;
        }}

        .potencial-wrapper {{
            position: relative; background: {C['POT_BKG']};
            border: 1px solid {C['BORDER']}; border-radius: 12px; height: 100%; padding: 1.2rem;
            display: flex; flex-direction: column; justify-content: center;
        }}
        .potencial-val {{ 
            font-size: 1.4rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; 
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}

        .timeline-item {{
            border-left: 2px solid {C['BORDER']};
            margin-left: 15px; padding-left: 20px; padding-bottom: 20px;
            position: relative;
        }}
        .timeline-item::before {{
            content: ''; position: absolute; left: -6px; top: 0;
            width: 10px; height: 10px; border-radius: 50%; background: #3232ff;
        }}
        .timeline-date {{ font-size: 0.8rem; color: {C['SUB']}; font-weight: 600; margin-bottom: 4px; }}
        .timeline-note {{ font-size: 0.95rem; color: {C['TEXT']}; margin: 0; line-height: 1.5; white-space: pre-wrap; }}
        
        audio {{ width: 100%; height: 35px; margin-top: 10px; border-radius: 8px; outline: none; }}

        [data-testid="stExpander"] {{ background-color: {C['CARD']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 12px !important; }}
        [data-testid="stExpander"] summary {{ background-color: transparent !important; }}
        [data-testid="stExpander"] p {{ font-size: 0.95rem !important; }}

        @media (max-width: 380px) {{ [data-testid="column"] {{ flex: 1 1 100% !important; min-width: 100% !important; }} }}
        @media (max-width: 768px) {{ .block-container {{ padding: 1.5rem 1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }} }}
        
        div[data-baseweb="select"] > div {{ background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important; border: 1px solid {C['BORDER']} !important; width: 100%; }}
        ul[role="listbox"], li[role="option"] {{ background-color: {C['SIDEBAR']} !important; color: {C['TEXT']} !important; }}
        hr {{ border-color: {C['BORDER']} !important; margin: 1.5rem 0 !important; }}
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
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:2rem;">Intelligence CRM (Supabase)</p>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Corporate ID")
            p = st.text_input("Security Token", type="password")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Access Denied.")
    st.stop()

# --- 7. DATA ENGINE ---
LEADS_BASE = [
    {
        "ID": 18,
        "Nome": "Elizabeth Sousa Rodrigues",
        "Empresa": "Emal Empresa de Mineração Aripuanã LTDA",
        "Cargo": "Diretor Executivo de Gente e Cultura",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Desenvolvimento de Lideranças",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Gestão da Mudança",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Todas",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Acima de 100 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 60,
        "LinkedIn": "",
        "Descrição Empresa": "Extração e processamento de minérios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 9,
        "Nome": "Carolina Bussadori",
        "Empresa": "Grupo St Marche",
        "Cargo": "Head de Gente & Cultura",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Recrutamento e Seleção",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "IA e Automação",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Acima de 100 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 60,
        "LinkedIn": "",
        "Descrição Empresa": "Rede de supermercados premium.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 7,
        "Nome": "Camila Alves Massaro",
        "Empresa": "ArcelorMittal Gonvarri",
        "Cargo": "Director of People, Strategy & IT",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Novos Modelos de Trabalho, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "Gestão de Mudança e Cultura Organizacional",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 58,
        "LinkedIn": "https://www.linkedin.com/in/camilamassaro-rh",
        "Descrição Empresa": "Processamento e distribuição de aço.",
        "Comentários Caio": "Temos contato, fizemos várias propostas negadas mas nunca foi vendido. quem tem contato lá é o victor pontello",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 5,
        "Nome": "Brenda Donato Endo",
        "Empresa": "Embracon",
        "Cargo": "Diretora de RH",
        "Quais desafios te trouxeram até aqui?": "Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Diversidade, Equidade e Inclusão (DE&I), Alinhamento Estratégico com a Alta Direção, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Cultura Organizacional, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "-",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 56,
        "LinkedIn": "https://www.linkedin.com/in/brenda-donato-endo-78275041",
        "Descrição Empresa": "Administradora de consórcios de bens.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 6,
        "Nome": "Bruno Szarf",
        "Empresa": "Stefanini",
        "Cargo": "VP Global",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados",
        "Tem interesse em conhecer parceiros": "Não",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "-",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 56,
        "LinkedIn": "https://www.linkedin.com/in/brunoszarf",
        "Descrição Empresa": "Consultoria e soluções em TI.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 33,
        "Nome": "Patrícia Rosado",
        "Empresa": "Tupy",
        "Cargo": "VP de Pessoas, Cultura e SSMA",
        "Quais desafios te trouxeram até aqui?": "Gestão da Cultura Híbrida, Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Nada específico, quero conhecer o que tiver relacionado",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 54,
        "LinkedIn": "https://www.linkedin.com/in/patricia-rosado-b15ba01a",
        "Descrição Empresa": "Metalúrgica e fundição de componentes.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 20,
        "Nome": "Franciele Ropelato",
        "Empresa": "Merck",
        "Cargo": "Diretora De RH",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Todas",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Acima de 100 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 54,
        "LinkedIn": "",
        "Descrição Empresa": "Indústria farmacêutica e química global.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 35,
        "Nome": "RITA SOUZA",
        "Empresa": "Bunge Alimentos",
        "Cargo": "Diretora Gestão Mudança Organizacional",
        "Quais desafios te trouxeram até aqui?": "Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Gestão da Mudança, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Adoção IA",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 54,
        "LinkedIn": "https://www.linkedin.com/in/rita-souza-neurochange/",
        "Descrição Empresa": "Processamento de grãos e óleos.",
        "Comentários Caio": "É cliente atual. Quem lidera a conta é o Mauricio e o Lourenço. Principal buyer é o Felipe Miana",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 38,
        "Nome": "Soraya Bahde",
        "Empresa": "Bradesco",
        "Cargo": "Diretora",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Gestão da Mudança, Cultura Organizacional, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "Qual é o prazo estimado para a sua": "Mais 18 meses",
        "Qual solução você gostaria de enten": "Treinamento e desenvolvimento",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Acima de 100 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 54,
        "LinkedIn": "https://www.linkedin.com/in/sorayabahde",
        "Descrição Empresa": "Serviços bancários e financeiros completos.",
        "Comentários Caio": "A finor conhece o pessoal de lá, acho que é o Tiago. é um cliente atual",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 32,
        "Nome": "Patricia Bobbato",
        "Empresa": "Natura",
        "Cargo": "Diretora de Cultura, Desenvolvimento, Bem estar e DE&I",
        "Quais desafios te trouxeram até aqui?": "Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Novos Modelos de Trabalho, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "EVP é Skill based",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 52,
        "LinkedIn": "https://www.linkedin.com/in/patriciabobbato",
        "Descrição Empresa": "Cosméticos e produtos de higiene.",
        "Comentários Caio": "Acho que tamo fazendo proposta lá. Quem tá liderando é o Mauricio aparentemente, mas acho que o Selli tem contexto. não é cliente, apenas lead",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 8,
        "Nome": "Camilla Padua",
        "Empresa": "KPMG Consultoria Ltda",
        "Cargo": "Sócia",
        "Quais desafios te trouxeram até aqui?": "Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Novos Modelos de Trabalho",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "Palestrante",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Palestrante",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 50,
        "LinkedIn": "",
        "Descrição Empresa": "Consultoria e auditoria corporativa.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 1"
    },
    {
        "ID": 13,
        "Nome": "Daniela Monteiro",
        "Empresa": "Editora do Brasil",
        "Cargo": "Diretora de RH & Marca",
        "Quais desafios te trouxeram até aqui?": "Adoção e Integração de IA/Automação",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "-",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "De 250 milhoes até 500 milhoes",
        "Score": 49,
        "LinkedIn": "https://br.linkedin.com/in/daniela-monteiro-a3125970",
        "Descrição Empresa": "Publicação de livros didáticos e literários.",
        "Comentários Caio": "Tamo tentando vender um projeto de agentes lá. Quem tem contato é o Selli",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 16,
        "Nome": "Diná Ribeiro de Carvalho",
        "Empresa": "Superlógica",
        "Cargo": "Diretora de Gente e Gestão",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Adoção e Integração de IA/Automação",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Aquisição e Retenção de Talentos, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Saúde Mental / IA para G&G",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "De 500 milhoes até 750 milhoes",
        "Score": 48,
        "LinkedIn": "https://br.linkedin.com/in/din%C3%A1-ribeiro-de-carvalho-a1a184348",
        "Descrição Empresa": "Software de gestão para condomínios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 31,
        "Nome": "Neto Mello",
        "Empresa": "Adimax",
        "Cargo": "Diretor de RH / CHRO",
        "Quais desafios te trouxeram até aqui?": "Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Recrutamento e Seleção, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Liderança e Cultura",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 48,
        "LinkedIn": "https://www.linkedin.com/in/netomello",
        "Descrição Empresa": "Fabricação de alimentos para pets.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 42,
        "Nome": "Willian Souza",
        "Empresa": "EMS",
        "Cargo": "Diretor de Governança e Treinamento",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Gestão da Mudança",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Treinamento e tomada de decisão apoiada por dados",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 48,
        "LinkedIn": "https://www.linkedin.com/in/willian-souza-63874147",
        "Descrição Empresa": "Indústria farmacêutica e medicamentos genéricos.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 15,
        "Nome": "Danila Pires Carsoso",
        "Empresa": "Motiva",
        "Cargo": "Diretor",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Aquisição e retenção de talentos",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 46,
        "LinkedIn": "",
        "Descrição Empresa": "Soluções de atendimento e telemarketing.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 21,
        "Nome": "Frederico Consetino Neto",
        "Empresa": "Afya",
        "Cargo": "Diretor de Recursos Humanos",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, Cibersegurança e Privacidade de Dados, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Construção de uma Proposta de Valor ao Empregado (EVP) Forte, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Benefícios Flexíveis, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Adoção e Integração de IA/Automação",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 46,
        "LinkedIn": "https://www.linkedin.com/in/frederico-cosentino-b67b1a20",
        "Descrição Empresa": "Educação médica e tecnologias digitais.",
        "Comentários Caio": "Contato antigo, que morreu faz tempo. acho que não temos mais contato hoje",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 22,
        "Nome": "Gerson Cosme santos",
        "Empresa": "GHT",
        "Cargo": "Diretor gente & performance",
        "Quais desafios te trouxeram até aqui?": "Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "Automação",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 46,
        "LinkedIn": "https://www.linkedin.com/in/gerson-cosme-santos",
        "Descrição Empresa": "Peças para máquinas pesadas (mineração).",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 2,
        "Nome": "Ana Luiza Guimarães Brasil",
        "Empresa": "Fortbras",
        "Cargo": "Diretor de Gente e Gestão",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "neste momento não tenho nenhuma",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 46,
        "LinkedIn": "https://www.linkedin.com/in/brasilana",
        "Descrição Empresa": "Distribuição de autopeças e serviços.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 36,
        "Nome": "Rosangela Schneider",
        "Empresa": "Karsten SA",
        "Cargo": "CHRO",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional, Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Aquisição e Retenção de Talentos, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "IA e automação no RH e na empresa",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "De 750 milhoes até 1bilhao",
        "Score": 45,
        "LinkedIn": "",
        "Descrição Empresa": "Indústria têxtil (cama, mesa e banho).",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 40,
        "Nome": "Thais Cristina de Abreu Vendramini Ferreira",
        "Empresa": "G5 Partners",
        "Cargo": "Vice President - People and Culture Manager",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Não",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Gostaria de entender melhor temas e possibilidades de como aplicar e ficar mais próximo dos exceutivos e decisores",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 43,
        "LinkedIn": "https://www.linkedin.com/in/thais-vendramini/",
        "Descrição Empresa": "Gestão de patrimônio e investimentos.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 4,
        "Nome": "Angelo Fanti",
        "Empresa": "Sorocaba Refrescos S/A",
        "Cargo": "Diretor Recursos Humanos",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Adoção e Integração de IA/Automação, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Impactos da IA na cultura organizacional",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "abaixo de 1 milhão",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "De 250 milhoes até 500 milhoes",
        "Score": 43,
        "LinkedIn": "https://br.linkedin.com/in/angelo-fanti-58a4a821",
        "Descrição Empresa": "Fabricação e distribuição de bebidas.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 25,
        "Nome": "Juliana Dorigo",
        "Empresa": "Grupo Ecoagro",
        "Cargo": "Diretora de RH",
        "Quais desafios te trouxeram até aqui?": "Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Cultura Organizacional, Gestão de Desempenho e Talentos",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "Alinhamento Estratégico com a Alta Direção",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 43,
        "LinkedIn": "https://www.linkedin.com/in/julianadorigorh",
        "Descrição Empresa": "Consultoria e estruturação de agronegócio.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 39,
        "Nome": "Tâmara Costa",
        "Empresa": "SantoDigital",
        "Cargo": "Diretora de RH",
        "Quais desafios te trouxeram até aqui?": "Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Recrutamento e Seleção, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Desenvolvimento de líderes, automação para RH",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "De 500 milhoes até 750 milhoes",
        "Score": 40,
        "LinkedIn": "https://www.linkedin.com/in/tamiscosta",
        "Descrição Empresa": "Consultoria em nuvem (Google Cloud).",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 28,
        "Nome": "Mariana Macedo Gaida",
        "Empresa": "Uncover",
        "Cargo": "Head of People",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Aquisição e Retenção de Talentos, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Automacao de RH",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 39,
        "LinkedIn": "",
        "Descrição Empresa": "Tecnologia e otimização de dados.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 1,
        "Nome": "Aldo Silva dos Santos",
        "Empresa": "HCOSTA",
        "Cargo": "CHRO Gente e Gestão",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "Saude Metal (NR1), DHO, Sistemas de Gestão RH",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 37,
        "LinkedIn": "https://www.linkedin.com/in/aldo-santos-a4985353/",
        "Descrição Empresa": "Escritório de advocacia e cobrança.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 23,
        "Nome": "GIOVANI CARRA",
        "Empresa": "ADF ONDULADOS E LOGISTICA",
        "Cargo": "DIRETOR DE RH",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "ALINHAMENTO ESTRATEGICO",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Abaixo de 500 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 37,
        "LinkedIn": "https://www.linkedin.com/in/giovani-carra-65858a33",
        "Descrição Empresa": "Embalagens de papelão e logística.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 10,
        "Nome": "Caroline Faki de Miranda",
        "Empresa": "Vigor Alimentos",
        "Cargo": "Head de Business Partner",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Novos Modelos de Trabalho, Automação de Processos no RH, Aquisição e Retenção de Talentos, Cultura Organizacional, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Sobre de IA",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Abaixo de 250milhoes",
        "Score": 37,
        "LinkedIn": "https://www.linkedin.com/in/caroline-faki-68338285",
        "Descrição Empresa": "Produção de laticínios e derivados.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 17,
        "Nome": "Diogo Dourado Soares",
        "Empresa": "Festo Brasil",
        "Cargo": "Head of HR CoE SAM",
        "Quais desafios te trouxeram até aqui?": "Gestão da Cultura Híbrida, Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Não",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Automação de processos para RH",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "De 250 milhoes até 500 milhoes",
        "Score": 37,
        "LinkedIn": "",
        "Descrição Empresa": "Automação industrial e pneumática.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 2"
    },
    {
        "ID": 27,
        "Nome": "Leonardo Rodrigues Gaspar",
        "Empresa": "SIMPRESS COMERCIO LOCACAO E SERVICOS LTDA",
        "Cargo": "Gerente Executivo de Recursos Humanos",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Cibersegurança e Privacidade de Dados, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap)",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Novos Modelos de Trabalho, Automação de Processos no RH, Aquisição e Retenção de Talentos, Recrutamento e Seleção, Gestão da Mudança, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Entender melhor soluções que integrem Inteligência Artificial aplicada a People Analytics, com foco em descentralização da informação para gestores e tomada de decisão mais ágil e orientada a dados.",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 32,
        "LinkedIn": "",
        "Descrição Empresa": "Outsourcing de equipamentos de TI e impressão.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 24,
        "Nome": "Jader Eder Bleil",
        "Empresa": "Greenbrier Maxion Equipamentos e Serviços Ferroviários S/A",
        "Cargo": "Gerente RT",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Gestão da Mudança, Cultura Organizacional, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "Aquisições e Retenção de Talentos",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 30,
        "LinkedIn": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225",
        "Descrição Empresa": "Vagões ferroviários e serviços industriais.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 14,
        "Nome": "Daniela Nishimoto",
        "Empresa": "Grupo L'Oréal",
        "Cargo": "Diretora/ Executiva de Relações Humanas",
        "Quais desafios te trouxeram até aqui?": "",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Outro",
        "Score": 29,
        "LinkedIn": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1",
        "Descrição Empresa": "Fabricação global de produtos cosméticos.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 43,
        "Nome": "Daniele Intrebartoli Costa",
        "Empresa": "Heineken",
        "Cargo": "Gerente Sr People",
        "Quais desafios te trouxeram até aqui?": "Saúde Mental e Bem-Estar, Inteligencia Artificial, Saude Mental e Bem estar, Produtividade, Date Analytics",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Saúde Corporativa e Bem Estar, Gestao treinamentos funcionais",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Gestao treinamentos funcionais",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 28,
        "LinkedIn": "",
        "Descrição Empresa": "Cervejaria e produção de bebidas.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 41,
        "Nome": "Thamires Cristina Alves Pedro Justino",
        "Empresa": "Alcoa Alumínio",
        "Cargo": "Gerente de RH",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Cibersegurança e Privacidade de Dados, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "Soluções global da gestão de ponto e folha de pagamento.",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 28,
        "LinkedIn": "https://www.linkedin.com/in/thamires-pedro-15287611b/",
        "Descrição Empresa": "Produção mundial de bauxita e alumínio.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 11,
        "Nome": "Daniel Peruchi",
        "Empresa": "Alcoa",
        "Cargo": "Gerente Sênior RH",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Cibersegurança e Privacidade de Dados, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "IA como serviço de atendimento aos funcionários",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 28,
        "LinkedIn": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9",
        "Descrição Empresa": "Produção mundial de bauxita e alumínio.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 37,
        "Nome": "Sabrina Geraldo Rosa Lemes",
        "Empresa": "GBMX",
        "Cargo": "Gerente EHS",
        "Quais desafios te trouxeram até aqui?": "Saúde Mental e Bem-Estar, Sustentabilidade e ESG no RH",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "Programas de saúde corporativos",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "De 500 milhoes até 750 milhoes",
        "Score": 28,
        "LinkedIn": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107",
        "Descrição Empresa": "Vagões ferroviários e serviços industriais.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 34,
        "Nome": "Ricardo Malvestite",
        "Empresa": "GBMX",
        "Cargo": "Gerente Sr RH",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "13 - 18 meses",
        "Qual solução você gostaria de enten": "Adoção e Integração de IA/Automação",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 28,
        "LinkedIn": "https://www.linkedin.com/in/ricardo-malvestite-74b1936",
        "Descrição Empresa": "Vagões ferroviários e serviços industriais.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 26,
        "Nome": "Lenita David Gilioli Pedreira de Freitas",
        "Empresa": "Flora Produtos",
        "Cargo": "Gerente executiva de RH",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Diversidade, Equidade e Inclusão (DE&I), Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Alinhamento Estratégico com a Alta Direção",
        "Tem interesse em conhecer parceiros": "Não",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Saúde Corporativa e Bem Estar, Diversidade e Inclusão",
        "Qual é o prazo estimado para a sua": "4 - 6 meses",
        "Qual solução você gostaria de enten": "Automação de processos e desenvolvimento continuo da liderança sem mais do mesmo",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 28,
        "LinkedIn": "https://www.linkedin.com/in/lenita-gilioli-freitas",
        "Descrição Empresa": "Cosméticos e limpeza doméstica (Minuano).",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 29,
        "Nome": "Michele Ferreira",
        "Empresa": "Confiança Supermercados",
        "Cargo": "Coordenadora de DHO",
        "Quais desafios te trouxeram até aqui?": "Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Saúde Corporativa e Bem Estar",
        "Qual é o prazo estimado para a sua": "Mais 18 meses",
        "Qual solução você gostaria de enten": "Desenvolvimento de liderança e bem-estar",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 5000 a 10000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 26,
        "LinkedIn": "https://www.linkedin.com/in/michele-ferreira-16401083",
        "Descrição Empresa": "Rede varejista de alimentos.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 44,
        "Nome": "Marianna Biagi Pache",
        "Empresa": "Emal - Empresa de Mineração Aripuanã",
        "Cargo": "Gerente de Gestão de Pessoas e Administrativo",
        "Quais desafios te trouxeram até aqui?": "Fui indicada a conhecer o evento.",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Recrutamento e Seleção, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "A eficiência das empresas.",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "De 250 milhoes até 500 milhoes",
        "Score": 23,
        "LinkedIn": "",
        "Descrição Empresa": "Extração e processamento de minérios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 3,
        "Nome": "ANDRE LUIZ EXPEDITO ARANHA",
        "Empresa": "SUPERLOGICA",
        "Cargo": "GERENTE DE REMUNERAÇÃO",
        "Quais desafios te trouxeram até aqui?": "Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados",
        "Tem interesse em conhecer parceiros": "Não",
        "Quais são as prioridades de investi": "Benefícios Flexíveis, Automação de Processos no RH, Saúde Corporativa e Bem Estar, Software de Gestão para RH",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "AUTOMAÇÃO E IA",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "De 500 milhoes até 750 milhoes",
        "Score": 22,
        "LinkedIn": "https://www.linkedin.com/in/andrelearanha",
        "Descrição Empresa": "Software de gestão para condomínios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 30,
        "Nome": "Nelson Simeoni Junior",
        "Empresa": "Superlógica",
        "Cargo": "Gerente de DHO",
        "Quais desafios te trouxeram até aqui?": "Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, People Analytics e Decisão Baseada em Dados, Atualização Constante de Habilidades (Skills Gap), Alinhamento Estratégico com a Alta Direção, Gestão de Mudança Organizacional",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "7 - 12 meses",
        "Qual solução você gostaria de enten": "DHO",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "De 500 milhoes até 750 milhoes",
        "Score": 20,
        "LinkedIn": "https://www.linkedin.com/in/nelsonsimeoni",
        "Descrição Empresa": "Software de gestão para condomínios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 3"
    },
    {
        "ID": 12,
        "Nome": "Daniela Matos Faria",
        "Empresa": "Zamp",
        "Cargo": "Dir de Talentos e Cultura",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, People Analytics e Decisão Baseada em Dados",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Aquisição e Retenção de Talentos",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "",
        "Sou responsável pela decisão e budg": "Eu sou o principal decisor (a) sobre a escolha",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "Acima de 10000",
        "Receita anual da empresa (em Reais)": "Outro",
        "Score": 19,
        "LinkedIn": "https://www.linkedin.com/in/daniela-matos-faria",
        "Descrição Empresa": "Operadora do Burger King e Popeyes.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "",
        "Tier Final": "Tier 4"
    },
    {
        "ID": 19,
        "Nome": "FERNANDO SPINELLI",
        "Empresa": "COMPANHIA DE CONCESSÕES RODOVIÁRIAS DO NOVO LITORAL DE SÃO PAULO - CNL Rodovias",
        "Cargo": "Gerente de RH e SSO",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Desenvolvimento de Lideranças, Adoção e Integração de IA/Automação, Construção de uma Proposta de Valor ao Empregado (EVP) Forte",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Automação de Processos no RH, Aquisição e Retenção de Talentos, Recrutamento e Seleção, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "Melhorar nossos processos de R&S, em especial a captação de candidatos.",
        "Sou responsável pela decisão e budg": "Eu influencio e participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões",
        "Número de funcionários:": "De 1000 a 5000 funcionários",
        "Receita anual da empresa (em Reais)": "Acima de 1bilhao",
        "Score": 19,
        "LinkedIn": "",
        "Descrição Empresa": "Concessionária de rodovias (Grupo CCR).",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 4"
    },
    {
        "ID": 45,
        "Nome": "Graziella Albuquerque",
        "Empresa": "Emal Empresa de Mineração Aripuanã LTDA",
        "Cargo": "Supervisora de RH",
        "Quais desafios te trouxeram até aqui?": "Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Desenvolvimento de Lideranças",
        "Tem interesse em conhecer parceiros": "Sim",
        "Quais são as prioridades de investi": "Treinamento e Desenvolvimento, Automação de Processos no RH, Aquisição e Retenção de Talentos, Recrutamento e Seleção, Cultura Organizacional",
        "Qual é o prazo estimado para a sua": "0 - 3 meses",
        "Qual solução você gostaria de enten": "Automações de processos, aquisição de software.",
        "Sou responsável pela decisão e budg": "Eu não tenho influência nem participo da tomada de decisão",
        "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões",
        "Número de funcionários:": "De 500 a 1000 funcionários",
        "Receita anual da empresa (em Reais)": "De 250 milhoes até 500 milhoes",
        "Score": 17,
        "LinkedIn": "",
        "Descrição Empresa": "Extração e processamento de minérios.",
        "Comentários Caio": "",
        "Foto": "",
        "Novo Lead": "SIM (Novo)",
        "Tier Final": "Tier 4"
    }
]

vol_total = 0

for l in LEADS_BASE:
    l['id'] = l.get('ID')
    l['nome'] = l.get('Nome', 'N/I')
    l['empresa'] = l.get('Empresa', 'N/I')
    l['cargo'] = l.get('Cargo', 'N/I')
    
    # Processar nível de decisão
    raw_decisor = str(l.get('Sou responsável pela decisão e budg', '')).lower()
    if 'principal decisor' in raw_decisor or 'sim' in raw_decisor:
        l['decisor'] = 'Sim'
    elif 'influenciador' in raw_decisor or 'participo' in raw_decisor:
        l['decisor'] = 'Parcial'
    else:
        l['decisor'] = 'Não'
        
    l['score'] = l.get('Score', 0)
    l['linkedin'] = l.get('LinkedIn', '#') if l.get('LinkedIn') else '#'
    
    # Mapeamento do Dossiê
    l['bio'] = l.get('Descrição Empresa', 'N/I')
    l['interesse'] = l.get('Quais são as prioridades de investi', 'N/I')
    l['desafios'] = l.get('Quais desafios te trouxeram até aqui?', 'N/I')
    l['orcamento_real'] = l.get('Qual é a estimativa do orçamento an', 'N/I')
    l['receita'] = l.get('Receita anual da empresa (em Reais)', 'N/I')
    l['funcionarios'] = l.get('Número de funcionários:', 'N/I')
    l['prazo'] = l.get('Qual é o prazo estimado para a sua', 'N/I')
    l['solucao'] = l.get('Qual solução você gostaria de enten', 'N/I')
    l['comentarios_caio'] = l.get('Comentários Caio', '')
    
    # Obter Tier e Potencial diretamente do JSON
    l['t'] = str(l.get('Tier Final', 'Tier 4')).strip()
    l['o'] = str(l.get('Qual é a estimativa do orçamento an', 'N/I')).strip()
    
    # Cores da Etiqueta
    if '1' in l['t']: l['c'] = 'pill-blue'
    elif '2' in l['t']: l['c'] = 'pill-magenta'
    else: l['c'] = 'pill-neutral'
    
    # Lógica de cálculo do Volume Pipeline para o Dashboard Executivo
    o_lower = str(l.get('Qual é a estimativa do orçamento an', '')).lower()
    if 'acima de 100' in o_lower: vol_total += 100_000_000
    elif '50 milhões até 100' in o_lower: vol_total += 75_000_000
    elif '10 milhões até 50' in o_lower: vol_total += 30_000_000
    elif '2 milhões até 10' in o_lower: vol_total += 6_000_000
    elif 'abaixo de 2' in o_lower or 'abaixo de 1' in o_lower: vol_total += 1_000_000

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
    c3.markdown(f'<div class="potencial-wrapper"><span class="metric-label" style="color:#8E8E93;">Volume Pipeline Est.</span><p class="potencial-val">> R$ {vol_total / 1000000:.1f}M</p></div>', unsafe_allow_html=True)
    
    st.divider()
    font_col = "#ffffff" if st.session_state.theme == 'dark' else "#1A1A1C"
    
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### Pipeline Health")
        df_sorted = df_leads.sort_values(by='score', ascending=False).head(10)
        fig_bar = px.bar(df_sorted, x='score', y='nome', orientation='h', color='t', color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_col, margin=dict(l=0,r=0,t=10,b=0), height=300, yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with g2:
        st.markdown("### Distribuição Estratégica")
        fig_donut = px.pie(df_leads, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_donut.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_col, margin=dict(l=0,r=0,t=10,b=0), height=300, showlegend=True, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_donut, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filtrar", ["Todos", "Tier 1", "Tier 2", "Tier 3", "Tier 4"], label_visibility="collapsed")
    f_leads = LEADS_BASE if sel == "Todos" else [l for l in LEADS_BASE if sel in l['t']]
    st.write("")
    
    for l in f_leads:
        bar = '<div class="tier-1-bar"></div>' if "Tier 1" in l['t'] else ""
        photo_html = get_photo_html(l['nome'], l.get('linkedin', '#'), "small")
        
        card = f"""<div class="lead-row">{bar}
        <div style="display:flex; align-items:center; gap:15px; margin-bottom:12px;">
            {photo_html}
            <div style="flex:1;">
                <strong style="font-size:1.15rem;">{l['nome']}</strong><br>
                <span class="subtext">{l['cargo']}</span>
            </div>
            <div style="text-align:right;"><span class="{l['c']}">{l['t']}</span></div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid rgba(128,128,128,0.2);">
            <span style="font-weight:600;">{l['empresa']}</span>
            <span class="{l['c']}" style="font-size: 0.85rem;">{l['o']}</span>
        </div></div>"""
        
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Analisar Perfil", key=f"b_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Pipeline", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    st.write("")
    
    photo_html = get_photo_html(l['nome'], l.get('linkedin', '#'), "large")
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:20px; margin-bottom:20px; flex-wrap:wrap;">
            {photo_html}
            <div>
                <h1 style="margin-bottom:0; font-size:2.2rem;">{l['nome']}</h1>
                <p class="subtext" style="font-size:1.1rem; margin-top:5px;">{l['cargo']} @ <strong>{l['empresa']}</strong></p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Classificação</p><p class="metric-value">{l["t"]}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Score</p><p class="metric-value">{l["score"]} pts</p></div>', unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    with c3: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisor</p><p class="metric-value">{l["decisor"]}</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="potencial-wrapper"><p class="metric-label" style="color:#8E8E93;">Potencial Est.</p><p class="potencial-val" style="font-size: 1.1rem;">{l["o"]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    
    with st.expander("📂 Visualizar Dossiê Completo"):
        ec1, ec2 = st.columns(2)
        ec1.markdown(f"**🏢 Receita:** {l.get('receita', 'N/I')}\n\n**👥 Funcionários:** {l.get('funcionarios', 'N/I')}\n\n**🎯 Desafios:** {l.get('desafios', 'N/I')}")
        ec2.markdown(f"**⏳ Prazo Investimento:** {l.get('prazo', 'N/I')}\n\n**🛠 Solução Desejada:** {l.get('solucao', 'N/I')}\n\n**💡 Interesses:** {l.get('interesse', 'N/I')}")
        if l.get('comentarios_caio'):
            st.markdown(f"**💬 Comentários Internos:** {l['comentarios_caio']}")
        if l.get('linkedin') and l['linkedin'] != "#": st.link_button("Abrir LinkedIn", l['linkedin'])

    st.divider()
    
    st.markdown("### Registro")
    st.markdown("<p class='subtext' style='font-size: 0.9rem; margin-bottom: 10px;'>Adicionar Novo Registro (Texto ou Áudio)</p>", unsafe_allow_html=True)
    
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota", placeholder="Descreva a interação ou novos insights...", label_visibility="collapsed")
        
        audio_val = None
        if hasattr(st, 'audio_input'):
            audio_val = st.audio_input("Gravar Voice Note (Opcional)")
        elif hasattr(st, 'experimental_audio_input'):
            audio_val = st.experimental_audio_input("Gravar Voice Note (Opcional)")

        if st.form_submit_button("Registrar Insight", type="primary", use_container_width=True):
            if txt.strip() or audio_val is not None:
                audio_url = None
                lid_safe = extract_linkedin_id(l['linkedin']) or str(l['id'])
                if audio_val is not None:
                    audio_url = upload_audio_to_supabase(audio_val.read(), lid_safe)
                
                save_note_to_supabase(lid_safe, txt.strip(), audio_url)
                st.rerun()
    
    st.write("")
    
    notas_supabase = load_notes_from_supabase(extract_linkedin_id(l['linkedin']) or str(l['id']))
    
    if not notas_supabase:
        st.info("Nenhuma interação registrada no banco de dados.")
    else:
        for n in notas_supabase:
            dt_obj = datetime.fromisoformat(n['created_at'].replace('Z', '+00:00'))
            dt_str = dt_obj.strftime("%d/%m/%Y %H:%M")
            
            st.markdown(f"""
            <div class="timeline-item">
                <p class="timeline-date">{dt_str}</p>
                <p class="timeline-note">{n.get('texto', '')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if n.get('audio_url'):
                st.audio(n['audio_url'])
