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

# --- 3. DEFINIÇÃO DA PALETA E INJEÇÃO CSS (BRUTE FORCE ZERO-BUG) ---
def apply_executive_styles():
    is_dark = st.session_state.theme == 'dark'
    
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
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

        /* --- CORREÇÃO DE INPUTS --- */
        .stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {{
            background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; border-radius: 8px !important;
            caret-color: #3232ff !important; padding: 12px !important; width: 100% !important;
        }}
        div[data-baseweb="textarea"], div[data-baseweb="input"] {{ background-color: transparent !important; }}
        .stTextArea label p, .stTextInput label p {{ color: {C['TEXT']} !important; font-weight: 500 !important; }}
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.8 !important; }}

        /* --- ESTILIZAÇÃO DE BOTÕES --- */
        button[kind="secondary"], button[kind="secondaryAction"], .stLinkButton > a {{
            background-color: {C['BTN_SEC']} !important; color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; border-radius: 8px !important;
            transition: all 0.2s ease !important; text-decoration: none !important;
            width: 100% !important; display: inline-flex; align-items: center; justify-content: center;
        }}
        button[kind="secondary"]:hover, .stLinkButton > a:hover {{ border-color: #3232ff !important; background-color: rgba(50, 50, 255, 0.05) !important; }}

        button[kind="primary"] {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important;
            border: none !important; border-radius: 8px !important; width: 100% !important; transition: all 0.3s ease !important;
        }}
        button[kind="primary"]:hover {{ transform: translateY(-1px) !important; box-shadow: 0 4px 15px rgba(50, 50, 255, 0.3) !important; }}

        /* --- CARDS DE LISTA DE LEADS --- */
        .lead-row {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px;
            padding: 1rem; margin-bottom: 0.8rem; position: relative; overflow: hidden; transition: all 0.2s ease;
        }}
        .lead-row:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.05); }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}

        /* =========================================
           NOVAS CLASSES: GRID 2X2 & TIMELINE C-LEVEL
           ========================================= */
        .custom-metric-card {{
            background-color: {C['CARD']};
            padding: 1.2rem;
            border-radius: 12px;
            margin-bottom: 10px;
            border: 1px solid {C['BORDER']};
            display: flex; flex-direction: column; justify-content: space-between;
            height: 100%; min-height: 105px;
        }}
        .metric-label {{ font-size: 0.85rem; color: {C['SUB']}; font-weight: 500; margin-bottom: 0.3rem; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 1.6rem; font-weight: 700; color: {C['TEXT']}; margin: 0; line-height: 1.2; }}
        
        .potential-value {{
            font-size: 1.6rem; font-weight: 800;
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin: 0; line-height: 1.2;
        }}
        
        .timeline-item {{
            border-left: 2px solid {C['BORDER']};
            margin-left: 10px; padding-left: 20px; padding-bottom: 20px;
            position: relative;
        }}
        .timeline-item::before {{
            content: ''; position: absolute; left: -6px; top: 0;
            width: 10px; height: 10px; border-radius: 50%;
            background: #3232ff;
        }}
        .timeline-date {{ font-size: 0.8rem; color: {C['SUB']}; font-weight: 600; margin-bottom: 4px; }}
        .timeline-note {{ font-size: 0.95rem; color: {C['TEXT']}; margin: 0; line-height: 1.5; }}

        /* Ajuste do Radio Button (Pills de Navegação) */
        div[role="radiogroup"] {{ flex-direction: row !important; gap: 15px; margin-bottom: 15px; }}

        /* --- MEDIA QUERIES RESPONSIVAS --- */
        @media (max-width: 768px) {{
            .block-container {{ padding: 2rem 1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }}
            [data-testid="stHorizontalBlock"] {{ display: flex !important; flex-wrap: nowrap !important; gap: 10px !important; }}
            [data-testid="column"] {{ flex: 1 1 calc(50% - 5px) !important; min-width: calc(50% - 5px) !important; width: calc(50% - 5px) !important; }}
            .metric-value, .potential-value {{ font-size: 1.3rem !important; }}
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
    if score >= 39: return "Tier 2", "R$ 500k - 1M", "pill-magenta" # Reformatado conforme solicitado
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
    
    # Custom 2x2 grid metrics for Dashboard
    d1, d2 = st.columns(2)
    d1.markdown(f'<div class="custom-metric-card"><p class="metric-label">Contas Totais</p><p class="metric-value">{len(df_leads)}</p></div>', unsafe_allow_html=True)
    d2.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisores</p><p class="metric-value">{len(df_leads[df_leads["decisor"] == "Sim"])}</p></div>', unsafe_allow_html=True)
    
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

# MODO DETALHES (GRID 2x2 CUSTOMIZADO & TIMELINE)
elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Pipeline", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    
    st.write("")
    st.markdown(f"<h2 style='margin-bottom:0;'>{l['nome']}</h2><p class='subtext' style='font-size:1.1rem;'>{l['cargo']} @ <strong>{l['empresa']}</strong></p>", unsafe_allow_html=True)
    if l['linkedin'] != "#": st.link_button("↗ Abrir LinkedIn", l['linkedin'], use_container_width=True)
    
    st.divider()
    
    # --- GRID 2x2 C-LEVEL ---
    st.markdown("### Perfil Detalhado")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Classificação</p><p class="metric-value">{l["t"]}</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Score</p><p class="metric-value">{l["score"]} pts</p></div>', unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisor</p><p class="metric-value">{l["decisor"]}</p></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Potencial</p><p class="potential-value">{l["o"]}</p></div>', unsafe_allow_html=True)
    
    st.divider()
    
    # --- SEÇÃO REGISTRO & TIMELINE ---
    st.markdown("### Registro")
    
    # Sistema de Navegação (Pills)
    nav_tab = st.radio("Navegação de Registro", ["Histórico de Interações", "Adicionar Nova Nota"], horizontal=True, label_visibility="collapsed")
    
    if nav_tab == "Adicionar Nova Nota":
        st.write("")
        with st.form("intel", clear_on_submit=True):
            txt = st.text_area("Adicionar Novo Registro:", placeholder="Digite o registro estratégico...")
            if st.form_submit_button("Salvar Nota", type="primary", use_container_width=True):
                if txt.strip():
                    st.session_state.notas_locais.insert(0, {"id": l['id'], "dt": datetime.now().strftime("%d/%m/%Y às %H:%M"), "txt": txt})
                    st.success("Nota salva com sucesso! Mude para o Histórico para visualizar.")
    else:
        st.write("")
        notas = [x for x in st.session_state.notas_locais if x['id'] == l['id']]
        if not notas:
            st.info("Ainda não há registros para este lead.")
        else:
            for n in notas:
                st.markdown(f"""
                <div class="timeline-item">
                    <p class="timeline-date">{n['dt']}</p>
                    <p class="timeline-note">{n['txt']}</p>
                </div>
                """, unsafe_allow_html=True)
