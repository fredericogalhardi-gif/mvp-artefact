import streamlit as st
import pandas as pd
import plotly.express as px
import hmac
from datetime import datetime

# --- 1. CONFIGURAÇÃO MOBILE-FIRST ---
st.set_page_config(
    page_title="Artefact | Strategy",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GESTÃO DE ESTADO E TEMA ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'notas_locais' not in st.session_state: st.session_state.notas_locais = []

# --- 3. INJEÇÃO CSS (ZERO-BUG & RESPONSIVE) ---
def apply_executive_styles():
    is_dark = st.session_state.theme == 'dark'
    
    # Dicionário Central de Cores
    C = {
        "BKG": "#0A0A0F" if is_dark else "#F7F8FA",
        "SIDEBAR": "#111116" if is_dark else "#FFFFFF",
        "TEXT": "#FFFFFF" if is_dark else "#1D1D1F",
        "SUB": "#888890" if is_dark else "#636366",
        "CARD": "rgba(255, 255, 255, 0.03)" if is_dark else "#FFFFFF",
        "BORDER": "rgba(255, 255, 255, 0.1)" if is_dark else "#E0E0E0",
        "INPUT_BKG": "rgba(255, 255, 255, 0.03)" if is_dark else "#FFFFFF",
        "BTN_SEC": "transparent" if is_dark else "#FFFFFF"
    }
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;800&display=swap');
        
        /* Aplicação Global */
        .stApp {{ background-color: {C['BKG']}; font-family: 'Inter', sans-serif; color: {C['TEXT']}; }}
        [data-testid="stSidebar"] {{ background-color: {C['SIDEBAR']} !important; border-right: 1px solid {C['BORDER']}; }}
        h1, h2, h3, h4, p, span, label {{ color: {C['TEXT']} !important; }}
        .subtext {{ color: {C['SUB']} !important; }}

        /* Título Artefact Gradient */
        .atf-gradient {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* --- CORREÇÃO DE INPUTS (TEXTAREA/INPUT) --- */
        .stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {{
            background-color: {C['INPUT_BKG']} !important;
            color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important;
            border-radius: 8px !important;
            caret-color: #3232ff !important;
            padding: 12px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }}
        div[data-baseweb="textarea"], div[data-baseweb="input"] {{ background-color: transparent !important; }}
        .stTextArea label p, .stTextInput label p {{ color: {C['TEXT']} !important; font-weight: 500 !important; }}
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.8 !important; }}

        /* --- ESTILIZAÇÃO DE BOTÕES --- */
        button[kind="secondary"], button[kind="secondaryAction"], .stLinkButton > a {{
            background-color: {C['BTN_SEC']} !important;
            color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            text-decoration: none !important;
            width: 100% !important; 
            display: inline-flex; align-items: center; justify-content: center;
        }}
        button[kind="secondary"]:hover, .stLinkButton > a:hover {{
            border-color: #3232ff !important;
            background-color: rgba(50, 50, 255, 0.05) !important;
        }}

        button[kind="primary"] {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }}
        button[kind="primary"]:hover {{
            background: linear-gradient(90deg, #4d4dff 0%, #ff33a1 100%) !important;
            box-shadow: 0 4px 15px rgba(50, 50, 255, 0.3) !important;
            transform: translateY(-1px) !important;
        }}

        /* --- CARTÕES & MÉTRICAS (FLEX & WRAP RESPONSIVO) --- */
        div[data-testid="stMetric"] {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1.2rem !important; height: 100%;
        }}
        
        /* Contêiner de colunas flexível (Não trava larguras) */
        div[data-testid="stHorizontalBlock"] {{
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 1rem !important;
            width: 100% !important;
        }}
        
        /* Colunas ocupam o máximo possível mas quebram se faltar espaço */
        [data-testid="column"] {{
            flex: 1 1 min-content !important;
            min-width: 120px !important; /* Limite mínimo antes de quebrar para baixo */
        }}

        .lead-row {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1rem; margin-bottom: 0.8rem;
            position: relative; overflow: hidden; transition: all 0.2s ease;
            width: 100% !important; box-sizing: border-box !important;
        }}
        .lead-row:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.05); }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}

        /* --- TWEAKS EXTREMOS PARA MOBILE (< 600px) --- */
        @media (max-width: 600px) {{
            .block-container {{
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 2rem !important;
                max-width: 100vw !important;
                overflow-x: hidden !important;
            }}
            div[data-testid="stMetric"] {{ padding: 0.8rem !important; }}
            div[data-testid="stMetricValue"] > div {{ font-size: 1.15rem !important; }}
            /* Se a tela for muito fina, os blocos empilham. Senão, ficam 2x2. */
            [data-testid="column"] {{ min-width: 40% !important; }} 
        }}

        /* Filtros/Selectbox */
        div[data-baseweb="select"] > div {{ background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important; border: 1px solid {C['BORDER']} !important; width: 100%; }}
        ul[role="listbox"], li[role="option"] {{ background-color: {C['SIDEBAR']} !important; color: {C['TEXT']} !important; }}
        hr {{ border-color: {C['BORDER']} !important; margin: 1.5rem 0 !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()

# --- 4. AUTH SEGURO ---
def check_login(user, pwd):
    try:
        val_u, val_p = st.secrets["APP_USER"], st.secrets["APP_PASS"]
        return hmac.compare_digest(user.encode('utf-8'), val_u.encode('utf-8')) and \
               hmac.compare_digest(pwd.encode('utf-8'), val_p.encode('utf-8'))
    except: return False

if not st.session_state.logado:
    st.write("\n" * 4)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<h1 class="atf-gradient" style="font-size:3rem; text-align:center;">Artefact</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:2rem;">Strategy Intelligence</p>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("User ID")
            p = st.text_input("Token", type="password")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Access Denied.")
    st.stop()

# --- 5. DATA ENGINE ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf", "score": 55},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP Cultura", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "score": 52},
    {"id": 3, "nome": "Aldo Silva", "empresa": "HCOSTA", "cargo": "CHRO", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/", "score": 50},
    {"id": 4, "nome": "Thais Ferreira", "empresa": "G5 Partners", "cargo": "VP People", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/thais-vendramini/", "score": 49},
    {"id": 5, "nome": "Mari Stela", "empresa": "HILTI", "cargo": "CHRO", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/mariribeiro", "score": 48},
    {"id": 6, "nome": "Brenda Endo", "empresa": "Embracon", "cargo": "Diretora RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041", "score": 47},
    {"id": 7, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/sorayabahde", "score": 46},
    {"id": 8, "nome": "Ana Luiza Brasil", "empresa": "Fortbras", "cargo": "Diretor Gente/Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brasilana", "score": 45},
    {"id": 9, "nome": "Daniela Faria", "empresa": "Zamp", "cargo": "Dir. Talentos", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-matos-faria", "score": 44},
    {"id": 10, "nome": "Patricia Bobbato", "empresa": "Natura", "cargo": "Dir. Cultura DE&I", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/patriciabobbato", "score": 43},
    {"id": 40, "nome": "Frederico Galhardi", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "#", "score": 13}
]

def get_meta(score):
    if score >= 48: return "Tier 1", "> R$ 1 Milhão", "pill-blue"
    if score >= 39: return "Tier 2", "R$ 500k - R$ 1M", "pill-magenta"
    return "Tier 3", "< R$ 500k", "pill-neutral"

for l in LEADS_BASE:
    l['t'], l['o'], l['c'] = get_meta(l['score'])

df_leads = pd.DataFrame(LEADS_BASE)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("📊 Overview", use_container_width=True, disabled=(st.session_state.view_mode=='dashboard')):
        st.session_state.view_mode='dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=(st.session_state.view_mode=='list')):
        st.session_state.view_mode='list'; st.rerun()
    st.divider()
    t_label = "🌙 Midnight Mode" if st.session_state.theme == 'dark' else "☀️ Platinum Mode"
    if st.button(t_label, use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logado = False; st.rerun()

# --- 7. VIEWS ---
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1>Visão Executiva</h1>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Contas Totais", len(df_leads))
    c2.metric("Decisores", len(df_leads[df_leads['decisor'] == 'Sim']))
    
    st.divider()
    font_color = "#ffffff" if st.session_state.theme == 'dark' else "#111111"
    
    st.markdown("### Distribuição de Classes")
    fig1 = px.bar(df_leads['t'].value_counts().reset_index(), x='count', y='t', orientation='h', color='t', color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), margin=dict(l=0,r=0,t=10,b=0), height=250)
    st.plotly_chart(fig1, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filtrar Classe", ["Todos", "Tier 1", "Tier 2", "Tier 3"])
    f_leads = LEADS_BASE if sel == "Todos" else [l for l in LEADS_BASE if sel in l['t']]
    st.write("")
    
    for l in f_leads:
        bar = '<div class="tier-1-bar"></div>' if "Tier 1" in l['t'] else ""
        card = f"""<div class="lead-row">{bar}
        <div style="display:flex; flex-wrap:wrap; justify-content:space-between; margin-bottom: 8px; gap: 8px;">
            <div style="flex: 1 1 auto;"><strong style="font-size: 1.1rem;">{l['nome']}</strong><br><span class="subtext">{l['cargo']}</span></div>
            <div style="text-align:right;"><span class="{l['c']}">{l['t']}</span></div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items: center; border-top: 1px solid { '#333' if st.session_state.theme == 'dark' else '#eee' }; padding-top: 8px;">
            <span style="font-weight: 500; font-size: 0.95rem;">{l['empresa']}</span>
            <span class="{l['c']}" style="font-size: 0.95rem;">{l['o']}</span>
        </div>
        </div>"""
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Abrir Perfil", key=f"b_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Pipeline", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    
    st.write("")
    st.markdown(f"<h2 style='margin-bottom:0;'>{l['nome']}</h2><p class='subtext' style='font-size:1.1rem;'>{l['cargo']} @ <strong>{l['empresa']}</strong></p>", unsafe_allow_html=True)
    if l['linkedin'] != "#": st.link_button("↗ Abrir LinkedIn", l['linkedin'], use_container_width=True)
    
    st.divider()
    
    # GRADE FLEXÍVEL RESPONSIVA (Grid Inteligente)
    c1, c2 = st.columns(2)
    c1.metric("Classificação", l['t'])
    c2.metric("Score", f"{l['score']} pts")
    
    st.write("")
    
    c3, c4 = st.columns(2)
    c3.metric("Decisor", l['decisor'])
    c4.metric("Potencial", l['o'])
    
    st.divider()
    st.markdown("### Inteligência Estratégica")
    
    with st.form("intel", clear_on_submit=True):
        txt = st.text_area("Novo Insight Estratégico:")
        if st.form_submit_button("Salvar Inteligência", type="primary", use_container_width=True):
            if txt.strip():
                st.session_state.notas_locais.insert(0, {"id": l['id'], "dt": datetime.now().strftime("%d/%m às %H:%M"), "txt": txt})
                st.rerun()
    
    st.markdown("#### Linha do Tempo")
    notas = [x for x in st.session_state.notas_locais if x['id'] == l['id']]
    if not notas:
        st.info("Nenhuma interação registrada.")
    else:
        bg_card = "rgba(255,255,255,0.03)" if st.session_state.theme == 'dark' else "#FFFFFF"
        bd_card = "rgba(255,255,255,0.08)" if st.session_state.theme == 'dark' else "#E0E0E0"
        for n in notas:
            st.markdown(f"<div style='background:{bg_card}; padding:15px; border-radius:8px; margin-bottom:10px; border:1px solid {bd_card}'><span class='subtext' style='font-size:0.75rem; font-weight:600;'>📅 {n['dt']}</span><p style='margin-top:5px; margin-bottom:0;'>{n['txt']}</p></div>", unsafe_allow_html=True)
