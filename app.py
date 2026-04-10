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

# --- 3. DEFINIÇÃO DA PALETA E INJEÇÃO CSS (BRUTE FORCE) ---
def apply_executive_styles():
    is_dark = st.session_state.theme == 'dark'
    
    # Variáveis de Cores Centrais
    C = {
        "BKG": "#0A0A0F" if is_dark else "#F7F8FA",
        "SIDEBAR": "#111116" if is_dark else "#FFFFFF",
        "TEXT": "#FFFFFF" if is_dark else "#1D1D1F",
        "SUB": "#888890" if is_dark else "#636366",
        "CARD": "rgba(255, 255, 255, 0.03)" if is_dark else "#FFFFFF",
        "BORDER": "rgba(255, 255, 255, 0.1)" if is_dark else "#D1D1D6",
        "INPUT_BKG": "rgba(255, 255, 255, 0.05)" if is_dark else "#FFFFFF",
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

        /* --- CORREÇÃO DE INPUTS (TEXT AREA / INPUT) --- */
        div[data-baseweb="textarea"], div[data-baseweb="input"], [data-testid="stForm"] {{
            background-color: {C['INPUT_BKG']} !important;
            border-radius: 8px !important;
        }}
        
        textarea, input {{
            color: {C['TEXT']} !important;
            background-color: transparent !important;
            caret-color: #3232ff !important;
        }}

        /* Placeholder contrast */
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.7; }}

        /* --- CORREÇÃO DE BOTÕES (SECONDARY/PRIMARY) --- */
        button[kind="secondary"], button[kind="secondaryAction"], .stLinkButton > a {{
            background-color: {C['BTN_SEC']} !important;
            color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            text-decoration: none !important;
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
        }}

        /* --- GRID 2X2 & CARDS --- */
        div[data-testid="stMetric"] {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1rem !important;
        }}

        @media (max-width: 640px) {{
            div[data-testid="stHorizontalBlock"] {{ flex-direction: row !important; gap: 0.5rem !important; }}
            div[data-testid="column"] {{ width: 50% !important; flex: 1 1 48% !important; }}
            div[data-testid="stMetricValue"] > div {{ font-size: 1.1rem !important; }}
        }}

        .lead-row {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1rem; margin-bottom: 0.8rem;
            position: relative; overflow: hidden;
        }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}

        /* Correção específica para Selectbox dropdown */
        div[data-baseweb="select"] > div {{ background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important; border: 1px solid {C['BORDER']} !important; }}
        ul[role="listbox"], li[role="option"] {{ background-color: {C['SIDEBAR']} !important; color: {C['TEXT']} !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()

# --- 4. AUTH & DATA ---
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
        with st.form("login"):
            u = st.text_input("User ID")
            p = st.text_input("Token", type="password")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Denied.")
    st.stop()

# --- 5. DATA ENGINE ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf", "score": 55},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP Cultura", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "score": 52},
    {"id": 3, "nome": "Aldo Silva", "empresa": "HCOSTA", "cargo": "CHRO", "decisor": "Sim", "linkedin": "#", "score": 50},
    {"id": 40, "nome": "Frederico Galhardi", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "#", "score": 13}
]

def get_meta(score):
    if score >= 48: return "Tier 1", "> R$ 1 Milhão", "pill-blue"
    if score >= 39: return "Tier 2", "R$ 500k - R$ 1M", "pill-magenta"
    return "Tier 3", "< R$ 500k", "pill-neutral"

for l in LEADS_BASE:
    l['t'], l['o'], l['c'] = get_meta(l['score'])

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("📊 Overview", use_container_width=True, disabled=(st.session_state.view_mode=='dashboard')):
        st.session_state.view_mode='dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=(st.session_state.view_mode=='list')):
        st.session_state.view_mode='list'; st.rerun()
    st.divider()
    t_label = "🌙 Midnight" if st.session_state.theme == 'dark' else "☀️ Platinum"
    if st.button(f"Theme: {t_label}", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logado = False; st.rerun()

# --- 7. VIEWS ---
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1>Visão Executiva</h1>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    df = pd.DataFrame(LEADS_BASE)
    c1.metric("Accounts", len(df))
    c2.metric("Decisores", len(df[df['decisor'] == 'Sim']))
    c3.metric("Avg Score", f"{df['score'].mean():.1f}")
    st.divider()
    fig = px.pie(df, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#888890", height=300, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filter", ["Todos", "Tier 1", "Tier 2", "Tier 3"])
    f_leads = LEADS_BASE if sel == "Todos" else [l for l in LEADS_BASE if sel in l['t']]
    
    for l in f_leads:
        bar = '<div class="tier-1-bar"></div>' if "Tier 1" in l['t'] else ""
        card = f"""<div class="lead-row">{bar}<div style="display:flex; justify-content:space-between;">
        <div><strong>{l['nome']}</strong><br><span class="subtext">{l['cargo']}</span></div>
        <div style="text-align:right"><span class="{l['c']}">{l['t']}</span><br><small>{l['o']}</small></div></div></div>"""
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Abrir {l['nome']}", key=f"b_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Back"): st.session_state.view_mode = 'list'; st.rerun()
    
    col_t, col_lk = st.columns([3,1])
    col_t.markdown(f"<h2>{l['nome']}</h2><p class='subtext'>{l['empresa']}</p>", unsafe_allow_html=True)
    if l['linkedin'] != "#": col_lk.link_button("LinkedIn", l['linkedin'], use_container_width=True)
    
    st.divider()
    # GRID 2x2 RIGOROSO
    r1_c1, r1_c2 = st.columns(2)
    r1_c1.metric("Classificação", l['t'])
    r1_c2.metric("Score", f"{l['score']} pts")
    
    r2_c1, r2_c2 = st.columns(2)
    r2_c1.metric("Decisor", l['decisor'])
    r2_c2.metric("Potencial", l['o'])
    
    st.divider()
    with st.form("intel", clear_on_submit=True):
        txt = st.text_area("Novo Insight Estratégico:")
        if st.form_submit_button("Salvar Inteligência", type="primary", use_container_width=True):
            st.session_state.notas_locais.insert(0, {"id": l['id'], "dt": datetime.now().strftime("%d/%m %H:%M"), "txt": txt})
            st.rerun()
    
    for n in [x for x in st.session_state.notas_locais if x['id'] == l['id']]:
        st.markdown(f"<div style='background:{st.session_state.theme=='dark' and 'rgba(255,255,255,0.03)' or '#FFFFFF'}; padding:10px; border-radius:8px; margin-bottom:10px; border:1px solid rgba(0,0,0,0.1)'><b>{n['dt']}</b>: {n['txt']}</div>", unsafe_allow_html=True)
