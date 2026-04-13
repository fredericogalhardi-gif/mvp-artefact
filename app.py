```python
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
DB_FILE = 'banco.json'

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

# --- 4. LÓGICA DE FOTOS DE PERFIL (/sabi) ---
def extract_linkedin_id(url):
    if not url or url == "#": return None
    parts = [p for p in url.split('/') if p]
    return parts[-1] if parts else None

def get_photo_html(name, url, size_class="large"):
    lid = extract_linkedin_id(url)
    if lid:
        path = os.path.join('sabi', f"{lid}.png")
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f'<img src="data:image/png;base64,{b64}" class="profile-pic {size_class}">'
            except: pass
    
    # Placeholder Elegante (Iniciais)
    initials = "".join([w[0] for w in name.split()[:2]]).upper()
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
        "METRIC_BKG": "#0A0A0F" if is_dark else "#FFFFFF"
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

        /* UX de Input (Zero-Bug no Platinum Mode) */
        .stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {{
            background-color: {C['INPUT_BKG']} !important; 
            color: {C['INPUT_TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; 
            border-radius: 8px !important;
            caret-color: #3232ff !important; 
            padding: 14px !important; 
            width: 100% !important;
            box-sizing: border-box !important; 
            font-size: 0.95rem !important;
        }}
        div[data-baseweb="textarea"], div[data-baseweb="input"] {{ background-color: transparent !important; border: none !important; }}
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.6 !important; }}

        /* Botões High-End */
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

        /* Fotos de Perfil Circulares */
        .profile-pic, .initials-placeholder {{
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #fff;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}
        .profile-pic.large, .initials-placeholder.large {{ width: 120px; height: 120px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; border-width: 1px; }}
        .initials-placeholder {{
            background: linear-gradient(135deg, #3232ff, #ff1493);
            color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800;
        }}
        .initials-placeholder.large {{ font-size: 2.5rem; }}
        .initials-placeholder.small {{ font-size: 1.2rem; }}

        /* Layout Cards (Pipeline) */
        .lead-row {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px;
            padding: 1.2rem; margin-bottom: 1rem; position: relative; overflow: hidden; transition: all 0.2s ease;
        }}
        .lead-row:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.05); }}
        .tier-1-bar {{ position: absolute; top: 0; left: 0; height: 4px; width: 100%; background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); }}

        /* Grid 2x2 Elástico */
        .custom-metric-card {{
            background-color: {C['METRIC_BKG']};
            padding: 1.2rem; border-radius: 10px; margin-bottom: 10px;
            border: 1px solid {C['BORDER']}; display: flex; flex-direction: column; justify-content: space-between;
            height: 100%; min-height: 110px;
        }}
        .metric-label {{ font-size: 0.85rem; color: {C['SUB']}; font-weight: 500; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 1.6rem; font-weight: 700; color: {C['TEXT']}; margin: 0; line-height: 1.2; }}
        
        .potential-value {{
            font-size: 1.6rem; font-weight: 800; margin: 0; line-height: 1.2;
            background: linear-gradient(90deg, #3232ff, #ff1493);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}

        /* Timeline de Interações */
        .timeline-item {{
            border-left: 2px solid {C['BORDER']};
            margin-left: 15px; padding-left: 20px; padding-bottom: 20px;
            position: relative;
        }}
        .timeline-item::before {{
            content: ''; position: absolute; left: -6px; top: 0;
            width: 10px; height: 10px; border-radius: 50%;
            background: #3232ff;
        }}
        .timeline-date {{ font-size: 0.8rem; color: {C['SUB']}; font-weight: 600; margin-bottom: 4px; }}
        .timeline-note {{ font-size: 0.95rem; color: {C['TEXT']}; margin: 0; line-height: 1.5; white-space: pre-wrap; }}

        /* Quebra Responsiva (Liquid Design) */
        div[data-testid="stHorizontalBlock"] {{ display: flex !important; flex-wrap: wrap !important; gap: 10px; }}
        [data-testid="column"] {{ flex: 1 1 calc(50% - 5px) !important; min-width: 140px !important; width: calc(50% - 5px) !important; }}

        @media (max-width: 768px) {{
            .block-container {{ padding: 1.5rem 1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }}
            .profile-pic.large, .initials-placeholder.large {{ width: 90px; height: 90px; font-size: 1.8rem; }}
        }}
        @media (max-width: 380px) {{
            [data-testid="column"] {{ flex: 1 1 100% !important; min-width: 100% !important; width: 100% !important; }}
        }}
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
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:2rem;">Intelligence CRM Golden</p>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Corporate ID")
            p = st.text_input("Security Token", type="password")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Access Denied.")
    st.stop()

# --- 7. DATA ENGINE ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "score": 55, "linkedin": "https://www.linkedin.com/in/brunoszarf"},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP Cultura", "decisor": "Sim", "score": 52, "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a"},
    {"id": 3, "nome": "Aldo Silva", "empresa": "HCOSTA", "cargo": "CHRO", "decisor": "Sim", "score": 50, "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353"},
    {"id": 4, "nome": "Thais Ferreira", "empresa": "G5 Partners", "cargo": "VP People", "decisor": "Sim", "score": 49, "linkedin": "https://www.linkedin.com/in/thais-vendramini"},
    {"id": 5, "nome": "Mari Stela", "empresa": "HILTI", "cargo": "CHRO", "decisor": "Sim", "score": 48, "linkedin": "https://www.linkedin.com/in/mariribeiro"},
    {"id": 6, "nome": "Brenda Endo", "empresa": "Embracon", "cargo": "Diretora RH", "decisor": "Sim", "score": 47, "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041"},
    {"id": 7, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "decisor": "Parcial", "score": 46, "linkedin": "https://www.linkedin.com/in/sorayabahde"},
    {"id": 8, "nome": "Ana Luiza Brasil", "empresa": "Fortbras", "cargo": "Dir. Gente", "decisor": "Sim", "score": 45, "linkedin": "https://www.linkedin.com/in/brasilana"},
    {"id": 9, "nome": "Daniela Faria", "empresa": "Zamp", "cargo": "Dir. Talentos", "decisor": "Sim", "score": 44, "linkedin": "https://www.linkedin.com/in/daniela-matos-faria"},
    {"id": 10, "nome": "Patricia Bobbato", "empresa": "Natura", "cargo": "Dir. Cultura", "decisor": "Parcial", "score": 43, "linkedin": "https://www.linkedin.com/in/patriciabobbato"}
]

def calc_est(score):
    if score >= 48: return "Tier 1", "> R$ 1 Milhão", "pill-blue", 1500000
    if score >= 39: return "Tier 2", "R$ 500k - 1M", "pill-magenta", 750000
    return "Tier 3", "< R$ 500k", "pill-neutral", 250000

vol_total = 0
for l in LEADS_BASE:
    l['t'], l['o'], l['c'], val = calc_est(l['score'])
    vol_total += val

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
    c3.markdown(f'<div class="custom-metric-card"><p class="metric-label">Volume Pipeline</p><p class="potential-value">> R$ {vol_total / 1000000:.1f}M</p></div>', unsafe_allow_html=True)
    
    st.divider()
    font_col = "#ffffff" if st.session_state.theme == 'dark' else "#1A1A1C"
    
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("### Pipeline Health")
        df_sorted = df_leads.sort_values(by='score', ascending=False).head(10)
        fig_bar = px.bar(df_sorted, x='score', y='nome', orientation='h', color='t', color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_col, margin=dict(l=0,r=0,t=10,b=0), height=300, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with g2:
        st.markdown("### Distribuição Estratégica")
        fig_donut = px.pie(df_leads, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig_donut.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_col, margin=dict(l=0,r=0,t=10,b=0), height=300, showlegend=True, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_donut, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filtrar", ["Todos", "Tier 1", "Tier 2", "Tier 3"], label_visibility="collapsed")
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
            <span class="{l['c']}">{l['o']}</span>
        </div></div>"""
        
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Analisar Perfil", key=f"b_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Pipeline", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    st.write("")
    
    # Header com Foto Circular
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
    
    # --- GRID 2x2 ---
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Classificação</p><p class="metric-value">{l["t"]}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Score</p><p class="metric-value">{l["score"]} pts</p></div>', unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    with c3: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisor</p><p class="metric-value">{l["decisor"]}</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Potencial</p><p class="potential-value">{l["o"]}</p></div>', unsafe_allow_html=True)
    
    st.divider()
    
    # --- SEÇÃO REGISTRO & TIMELINE FÍSICA ---
    st.markdown("### Registro")
    st.markdown("<p class='subtext' style='font-size: 0.9rem; margin-bottom: 10px;'>Adicionar Novo Registro</p>", unsafe_allow_html=True)
    
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota", placeholder="Descreva a interação ou novos insights...", label_visibility="collapsed")
        if st.form_submit_button("Salvar Nota", type="primary", use_container_width=True):
            if txt.strip():
                nova_nota = {"id_lead": l['id'], "dt": datetime.now().strftime("%d/%m/%Y %H:%M"), "txt": txt}
                st.session_state.notas_locais.insert(0, nova_nota)
                save_notes(st.session_state.notas_locais)
                st.rerun()
    
    st.write("")
    
    notas = [x for x in st.session_state.notas_locais if x.get('id_lead') == l['id']]
    if not notas:
        st.info("Nenhuma interação registrada no banco de dados.")
    else:
        for n in notas:
            st.markdown(f"""
            <div class="timeline-item">
                <p class="timeline-date">{n['dt']}</p>
                <p class="timeline-note">{n['txt']}</p>
            </div>
            """, unsafe_allow_html=True)
```
