import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

# --- 2. SUPABASE CONNECTION ---
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Erro Crítico: Credenciais do Supabase não encontradas.")
        st.stop()

supabase = get_supabase_client()

def load_notes_from_supabase(lead_id: str):
    try:
        response = supabase.table("notas").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        return []

def save_note_to_supabase(lead_id: str, texto: str, audio_url: str = None):
    try:
        data = {"lead_id": str(lead_id), "texto": texto, "created_at": datetime.now().isoformat()}
        if audio_url: data["audio_url"] = audio_url
        supabase.table("notas").insert(data).execute()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def delete_note_from_supabase(note_id: str):
    try:
        supabase.table("notas").delete().eq("id", note_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar: {e}")
        return False

def upload_audio_to_supabase(audio_bytes, lead_id: str):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_lead_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))
        filename = f"registro_{safe_lead_id}_{timestamp}.wav"
        supabase.storage.from_("gravacoes").upload(file=audio_bytes, path=filename, file_options={"content-type": "audio/wav"})
        return supabase.storage.from_("gravacoes").get_public_url(filename)
    except Exception:
        return None

# --- 3. GESTÃO DE ESTADO ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'

# --- 4. LÓGICA DE FOTOS ---
SABI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sabi')

def extract_linkedin_id(url):
    if not url or url == "#" or str(url) == 'nan': return None
    return url.rstrip('/').split('/')[-1]

def get_photo_html(name, url, size_class="large"):
    lid = extract_linkedin_id(url)
    if lid:
        file_prefix = f"httpswww.linkedin.comin{lid}"
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG']:
            test_path = os.path.join(SABI_DIR, f"{file_prefix}{ext}")
            if os.path.exists(test_path):
                with open(test_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f'<img src="data:image/png;base64,{b64}" class="profile-pic {size_class}">'
    initials = "".join([w[0] for w in str(name).split()[:2]]).upper()
    return f'<div class="initials-placeholder {size_class}">{initials}</div>'

# --- 5. DESIGN SYSTEM ---
def apply_executive_styles():
    is_dark = st.session_state.theme == 'dark'
    C = {
        "BKG": "#050508" if is_dark else "#F4F5F7",
        "SIDEBAR": "#0A0A0F" if is_dark else "#FFFFFF",
        "TEXT": "#FFFFFF" if is_dark else "#1A1A1C",
        "SUB": "#8E8E93" if is_dark else "#636366",
        "CARD": "rgba(255, 255, 255, 0.02)" if is_dark else "#FFFFFF",
        "BORDER": "rgba(255, 255, 255, 0.2)" if is_dark else "#D1D1D6",
        "INPUT_BKG": "rgba(255, 255, 255, 0.04)" if is_dark else "#FFFFFF",
        "INPUT_TEXT": "#FFFFFF" if is_dark else "#000000"
    }
    btn_border = "#3232ff" if is_dark else "#D1D1D6"
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {C['BKG']}; font-family: 'Inter', sans-serif; color: {C['TEXT']}; }}
        [data-testid="stSidebar"] {{ background-color: {C['SIDEBAR']} !important; border-right: 1px solid {C['BORDER']}; }}
        .atf-gradient {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}
        .stTextArea textarea, .stTextInput input {{ background-color: {C['INPUT_BKG']} !important; color: {C['INPUT_TEXT']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 8px !important; }}
        button[kind="secondary"] {{ background-color: transparent !important; color: {C['TEXT']} !important; border: 1px solid {btn_border} !important; border-radius: 8px !important; width: 100% !important; }}
        button[kind="primary"] {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; width: 100% !important; font-weight: 600 !important; }}
        button[disabled] {{ border: 1px solid #3232ff !important; background-color: rgba(50, 50, 255, 0.1) !important; color: #FFFFFF !important; opacity: 1 !important; }}
        .profile-pic, .initials-placeholder {{ border-radius: 50%; object-fit: cover; border: 2px solid #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .profile-pic.large, .initials-placeholder.large {{ width: 100px; height: 100px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; }}
        .initials-placeholder {{ background: linear-gradient(135deg, #3232ff, #ff1493); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; }}
        .lead-row {{ background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; position: relative; }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}
        div[data-testid="stMetric"] {{ background: {"#0A0A0F" if is_dark else "#FFFFFF"}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1rem !important; }}
        .timeline-item {{ border-left: 2px solid {C['BORDER']}; margin-left: 15px; padding-left: 20px; padding-bottom: 20px; position: relative; }}
        .timeline-item::before {{ content: ''; position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: #3232ff; }}
        .delete-btn {{ color: #ff4b4b; cursor: pointer; font-size: 0.8rem; text-decoration: underline; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()

# --- 6. DATABASE ---
LEADS_BASE = [
    {"ID": 18, "Nome": "Elizabeth Sousa Rodrigues", "Empresa": "Grupo Mendes", "Cargo": "Diretor Executivo de Gente e Cultura", "Score": 60, "LinkedIn": "https://www.linkedin.com/in/elizabeth-sousa-rodrigues-26086518/", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Acima de 100 milhões"},
    {"ID": 9, "Nome": "Carolina Bussadori", "Empresa": "Grupo St Marche", "Cargo": "Head de Gente & Cultura", "Score": 60, "LinkedIn": "linkedin.com/in/carolinabussadorirh/", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Acima de 100 milhões"},
    {"ID": 7, "Nome": "Camila Alves Massaro", "Empresa": "ArcelorMittal Gonvarri", "Cargo": "Director of People, Strategy & IT", "Score": 58, "LinkedIn": "https://www.linkedin.com/in/camilamassaro-rh", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões"},
    {"ID": 5, "Nome": "Brenda Donato Endo", "Empresa": "Embracon", "Cargo": "Diretora de RH", "Score": 56, "LinkedIn": "https://www.linkedin.com/in/brenda-donato-endo-78275041", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões"},
    {"ID": 42, "Nome": "Willian Souza", "Empresa": "EMS", "Cargo": "Diretor de Governança e Treinamento", "Score": 55, "LinkedIn": "https://www.linkedin.com/in/willian-souza-63874147", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 15, "Nome": "Danila Pires Carsoso", "Empresa": "Motiva", "Cargo": "Diretor", "Score": 55, "LinkedIn": "", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 21, "Nome": "Frederico Consetino Neto", "Empresa": "Afya", "Cargo": "Diretor de Recursos Humanos", "Score": 55, "LinkedIn": "https://www.linkedin.com/in/freico-cosentino-b67b1a20", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 33, "Nome": "Patrícia Rosado", "Empresa": "Tupy", "Cargo": "VP de Pessoas, Cultura e SSMA", "Score": 54, "LinkedIn": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 20, "Nome": "Franciele Ropelato", "Empresa": "Merck", "Cargo": "Diretora De RH", "Score": 54, "LinkedIn": "", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Acima de 100 milhões"},
    {"ID": 35, "Nome": "RITA SOUZA", "Empresa": "Bunge Alimentos", "Cargo": "Diretora Gestão Mudança Organizacional", "Score": 54, "LinkedIn": "https://www.linkedin.com/in/rita-souza-neurochange/", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 38, "Nome": "Soraya Bahde", "Empresa": "Bradesco", "Cargo": "Diretora", "Score": 54, "LinkedIn": "https://www.linkedin.com/in/sorayabahde", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Acima de 100 milhões"},
    {"ID": 32, "Nome": "Patricia Bobbato", "Empresa": "Natura", "Cargo": "Diretora de Cultura, Desenvolvimento, Bem estar e DE&I", "Score": 52, "LinkedIn": "https://www.linkedin.com/in/patriciabobbato", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 13, "Nome": "Daniela Monteiro", "Empresa": "Editora do Brasil", "Cargo": "Diretora de RH & Marca", "Score": 49, "LinkedIn": "https://br.linkedin.com/in/daniela-monteiro-a3125970", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões"},
    {"ID": 16, "Nome": "Diná Ribeiro de Carvalho", "Empresa": "Superlógica", "Cargo": "Diretora de Gente e Gestão", "Score": 48, "LinkedIn": "https://br.linkedin.com/in/din%C3%A1-ribeiro-de-carvalho-a1a184348", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 31, "Nome": "Neto Mello", "Empresa": "Adimax", "Cargo": "Diretor de RH / CHRO", "Score": 48, "LinkedIn": "https://www.linkedin.com/in/netomello", "Tier Final": "Tier 1", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 22, "Nome": "Gerson Cosme santos", "Empresa": "GHT", "Cargo": "Diretor gente & performance", "Score": 46, "LinkedIn": "https://www.linkedin.com/in/gerson-cosme-santos", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 2, "Nome": "Ana Luiza Guimarães Brasil", "Empresa": "Fortbras", "Cargo": "Diretor de Gente e Gestão", "Score": 46, "LinkedIn": "https://www.linkedin.com/in/brasilana", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 36, "Nome": "Rosangela Schneider", "Empresa": "Karsten SA", "Cargo": "CHRO", "Score": 45, "LinkedIn": "", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 40, "Nome": "Thais Cristina de Abreu Vendramini Ferreira", "Empresa": "G5 Partners", "Cargo": "Vice President - People and Culture Manager", "Score": 43, "LinkedIn": "https://www.linkedin.com/in/thais-vendramini/", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 4, "Nome": "Angelo Fanti", "Empresa": "Sorocaba Refrescos S/A", "Cargo": "Diretor Recursos Humanos", "Score": 43, "LinkedIn": "https://br.linkedin.com/in/angelo-fanti-58a4a821", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "abaixo de 1 milhão"},
    {"ID": 25, "Nome": "Juliana Dorigo", "Empresa": "Grupo Ecoagro", "Cargo": "Diretora de RH", "Score": 43, "LinkedIn": "https://www.linkedin.com/in/julianadorigorh", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 39, "Nome": "Tâmara Costa", "Empresa": "SantoDigital", "Cargo": "Diretora de RH", "Score": 40, "LinkedIn": "https://www.linkedin.com/in/tamiscosta", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 1, "Nome": "Aldo Silva dos Santos", "Empresa": "HCOSTA", "Cargo": "CHRO Gente e Gestão", "Score": 37, "LinkedIn": "https://www.linkedin.com/in/aldo-santos-a4985353/", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 23, "Nome": "GIOVANI CARRA", "Empresa": "ADF ONDULADOS E LOGISTICA", "Cargo": "DIRETOR DE RH", "Score": 37, "LinkedIn": "https://www.linkedin.com/in/giovani-carra-65858a33", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 10, "Nome": "Caroline Faki de Miranda", "Empresa": "Vigor Alimentos", "Cargo": "Head de Business Partner", "Score": 37, "LinkedIn": "https://www.linkedin.com/in/caroline-faki-68338285", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 17, "Nome": "Diogo Dourado Soares", "Empresa": "Festo Brasil", "Cargo": "Head of HR CoE SAM", "Score": 37, "LinkedIn": "", "Tier Final": "Tier 2", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 27, "Nome": "Leonardo Rodrigues Gaspar", "Empresa": "SIMPRESS", "Cargo": "Gerente Executivo RH", "Score": 32, "LinkedIn": "", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 50 milhões até 100 milhões"},
    {"ID": 24, "Nome": "Jader Eder Bleil", "Empresa": "Greenbrier Maxion", "Cargo": "Gerente RT", "Score": 30, "LinkedIn": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões"},
    {"ID": 14, "Nome": "Daniela Nishimoto", "Empresa": "Grupo L'Oréal", "Cargo": "CHRO", "Score": 29, "LinkedIn": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "-"},
    {"ID": 43, "Nome": "Daniele Intrebartoli Costa", "Empresa": "Heineken", "Cargo": "Gerente Sr People", "Score": 28, "LinkedIn": "", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 41, "Nome": "Thamires Justino", "Empresa": "Alcoa Alumínio", "Cargo": "Gerente de RH", "Score": 28, "LinkedIn": "https://www.linkedin.com/in/thamires-pedro-15287611b/", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 11, "Nome": "Daniel Peruchi", "Empresa": "Alcoa", "Cargo": "Gerente Sênior RH", "Score": 28, "LinkedIn": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 37, "Nome": "Sabrina Lemes", "Empresa": "GBMX", "Cargo": "Gerente EHS", "Score": 28, "LinkedIn": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 34, "Nome": "Ricardo Malvestite", "Empresa": "GBMX", "Cargo": "Gerente Sr RH", "Score": 28, "LinkedIn": "https://www.linkedin.com/in/ricardo-malvestite-74b1936", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 26, "Nome": "Lenita David Gilioli", "Empresa": "Flora Produtos", "Cargo": "Gerente executiva RH", "Score": 28, "LinkedIn": "https://www.linkedin.com/in/lenita-gilioli-freitas", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 28, "Nome": "Mariana Macedo Gaida", "Empresa": "Uncover", "Cargo": "Head of People", "Score": 18, "LinkedIn": "", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 29, "Nome": "Michele Ferreira", "Empresa": "Confiança Supermercados", "Cargo": "Coordenadora de DHO", "Score": 26, "LinkedIn": "https://www.linkedin.com/in/michele-ferreira-16401083", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 44, "Nome": "Marianna Biagi Pache", "Empresa": "Emal", "Cargo": "Gerente de Gestão de Pessoas", "Score": 23, "LinkedIn": "", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 3, "Nome": "ANDRE LUIZ EXPEDITO ARANHA", "Empresa": "SUPERLOGICA", "Cargo": "GERENTE DE REMUNERAÇÃO", "Score": 22, "LinkedIn": "https://www.linkedin.com/in/andrelearanha", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 30, "Nome": "Nelson Simeoni Junior", "Empresa": "Superlógica", "Cargo": "Gerente de DHO", "Score": 20, "LinkedIn": "https://www.linkedin.com/in/nelsonsimeoni", "Tier Final": "Tier 3", "Qual é a estimativa do orçamento an": "Abaixo de 2 milhões"},
    {"ID": 12, "Nome": "Daniela Matos Faria", "Empresa": "Zamp", "Cargo": "Dir de Talentos e Cultura", "Score": 19, "LinkedIn": "https://www.linkedin.com/in/daniela-matos-faria", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 19, "Nome": "FERNANDO SPINELLI", "Empresa": "CNL Rodovias", "Cargo": "Gerente de RH e SSO", "Score": 19, "LinkedIn": "", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões"},
    {"ID": 45, "Nome": "Graziella Albuquerque", "Empresa": "Emal", "Cargo": "Supervisora de RH", "Score": 17, "LinkedIn": "", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "De 2 milhões até 10 milhões"},
    {"ID": 6, "Nome": "Bruno Szarf", "Empresa": "Stefanini", "Cargo": "VP Global", "Score": 0, "LinkedIn": "https://www.linkedin.com/in/brunoszarf", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "De 10 milhões até 50 milhões"},
    {"ID": 8, "Nome": "Camilla Padua", "Empresa": "KPMG", "Cargo": "Sócia", "Score": 0, "LinkedIn": "httpswww.linkedin.comincamillapadua", "Tier Final": "Tier 4", "Qual é a estimativa do orçamento an": "Palestrante"}
]

# --- 7. LOGIC ---
vol_total = 0
for l in LEADS_BASE:
    l['t'] = l.get('Tier Final', 'Tier 4')
    l['o'] = l.get('Qual é a estimativa do orçamento an', 'N/I')
    l['c'] = 'pill-blue' if '1' in l['t'] else 'pill-magenta' if '2' in l['t'] else 'pill-neutral'
    o_low = str(l['o']).lower()
    if '100 milhões' in o_low: vol_total += 100_000_000
    elif '50 milhões' in o_low: vol_total += 75_000_000
    elif '10 milhões' in o_low: vol_total += 30_000_000
    elif '2 milhões' in o_low: vol_total += 6_000_000
    else: vol_total += 1_000_000

df_leads = pd.DataFrame(LEADS_BASE)

# --- 8. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("📊 Executive Dash", use_container_width=True, disabled=(st.session_state.view_mode=='dashboard')): st.session_state.view_mode='dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=(st.session_state.view_mode=='list')): st.session_state.view_mode='list'; st.rerun()
    st.divider()
    if st.button("🌓 Toggle Theme", use_container_width=True): st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()

# --- 9. VIEWS ---
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1>Overview</h1>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Contas", len(df_leads))
    c2.metric("Tier 1", len(df_leads[df_leads['t'] == "Tier 1"]))
    c3.markdown(f'<div class="potencial-wrapper"><p class="potencial-val">> R$ {vol_total / 1000000:.1f}M</p></div>', unsafe_allow_html=True)
    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(px.pie(df_leads, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890']).update_layout(showlegend=False, height=300, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with g2:
        st.plotly_chart(px.bar(df_leads.sort_values('Score').tail(8), x='Score', y='Nome', orientation='h', color_discrete_sequence=['#3232ff']).update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Pipeline</h1>', unsafe_allow_html=True)
    search = st.text_input("🔍 Pesquisar por nome ou empresa...", placeholder="Digite aqui...")
    f_leads = [l for l in LEADS_BASE if search.lower() in l['Nome'].lower() or search.lower() in l['Empresa'].lower()]
    for l in f_leads:
        bar = '<div class="tier-1-bar"></div>' if "Tier 1" in l['t'] else ""
        card = f"""<div class="lead-row">{bar}<div style="display:flex; align-items:center; gap:15px;">{get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}<div style="flex:1;"><strong>{l['Nome']}</strong><br><span class="subtext">{l['Cargo']}</span></div><span class="{l['c']}">{l['t']}</span></div></div>"""
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Ver Perfil", key=f"v_{l['ID']}", use_container_width=True): st.session_state.selected_lead_id = l['ID']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['ID'] == st.session_state.selected_lead_id)
    if st.button("← Voltar", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    st.markdown(f"""<div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">{get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}<div><h1 style="margin:0;">{l['Nome']}</h1><p class="subtext">{l['Cargo']} @ {l['Empresa']}</p></div></div>""", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tier", l['t'])
    c2.metric("Score", f"{l['Score']} pts")
    c3.metric("Potencial", l['o'])
    c4.metric("Empresa", "Top" if "1" in l['t'] else "Média")
    
    with st.expander("📂 Dossiê Completo"):
        st.write(f"**Interesses:** {l.get('interesse', 'N/I')}")
        st.write(f"**Desafios:** {l.get('desafios', 'N/I')}")
        if l['LinkedIn']: st.link_button("Abrir LinkedIn", l['LinkedIn'])

    st.divider()
    st.markdown("### Registro")
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota", placeholder="Insights...", label_visibility="collapsed")
        audio = st.audio_input("Voz") if hasattr(st, 'audio_input') else None
        if st.form_submit_button("Registrar Insight", type="primary"):
            url = upload_audio_to_supabase(audio.read(), l['LinkedIn']) if audio else None
            save_note_to_supabase(extract_linkedin_id(l['LinkedIn']) or str(l['ID']), txt, url)
            st.rerun()
    
    for n in load_notes_from_supabase(extract_linkedin_id(l['LinkedIn']) or str(l['ID'])):
        dt = datetime.fromisoformat(n['created_at'].replace('Z', '+00:00')).strftime("%d/%m %H:%M")
        st.markdown(f"""<div class="timeline-item"><p class="timeline-date">{dt}</p><p>{n['texto']}</p></div>""", unsafe_allow_html=True)
        if n.get('audio_url'): st.audio(n['audio_url'])
        if st.button("🗑️ Deletar", key=f"del_{n['id']}"):
            if delete_note_from_supabase(n['id']): st.rerun()
