import streamlit as st
import pandas as pd
import plotly.express as px
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

# --- 4. LIQUID DESIGN ENGINE (CSS ULTRA-RESPONSIVO) ---
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
        "BTN_SEC": "transparent" if is_dark else "#FFFFFF",
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

        /* Inputs & Textareas */
        .stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input {{
            background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important;
            border: 1px solid {C['BORDER']} !important; border-radius: 8px !important;
            caret-color: #3232ff !important; padding: 14px !important; width: 100% !important;
            box-sizing: border-box !important; font-size: 0.95rem !important;
        }}
        div[data-baseweb="textarea"], div[data-baseweb="input"] {{ background-color: transparent !important; border: none !important; }}
        ::placeholder {{ color: {C['SUB']} !important; opacity: 0.6 !important; }}

        /* Botões C-Level */
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

        /* Grid 2x2 Elástico */
        div[data-testid="stMetric"] {{
            background: {C['CARD']}; border: 1px solid {C['BORDER']};
            border-radius: 12px; padding: 1.2rem !important; height: 100%;
        }}
        div[data-testid="stHorizontalBlock"] {{
            display: flex !important; flex-wrap: wrap !important; gap: 1rem !important; width: 100% !important;
        }}
        [data-testid="column"] {{
            flex: 1 1 40% !important; min-width: 140px !important; box-sizing: border-box !important;
        }}

        /* Card Potencial Estilizado (Premium) */
        .potencial-wrapper {{
            position: relative; background: {C['POT_BKG']};
            border: 1px solid {C['BORDER']}; border-radius: 12px; height: 100%; padding: 1.2rem;
            display: flex; flex-direction: column; justify-content: center;
        }}
        .potencial-val {{ 
            font-size: 1.8rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; 
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}

        /* Profile Picture (Circular) */
        .profile-wrapper {{ display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }}
        .profile-pic {{ 
            width: 80px; height: 80px; border-radius: 50%; object-fit: cover; 
            border: 2px solid {C['BORDER']}; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }}

        /* Timeline (Chat Bubbles) */
        .chat-bubble {{
            background: {C['INPUT_BKG']}; border: 1px solid {C['BORDER']};
            border-radius: 2px 16px 16px 16px; padding: 14px 18px; margin-bottom: 16px;
            max-width: 90%; position: relative;
        }}

        /* Expander Customizado */
        [data-testid="stExpander"] {{ background-color: {C['CARD']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 12px !important; }}
        [data-testid="stExpander"] summary {{ background-color: transparent !important; }}

        /* Quebra Responsiva Extrema */
        @media (max-width: 380px) {{ [data-testid="column"] {{ flex: 1 1 100% !important; min-width: 100% !important; }} }}
        @media (max-width: 768px) {{ .block-container {{ padding: 1.5rem 1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }} }}
        
        div[data-baseweb="select"] > div {{ background-color: {C['INPUT_BKG']} !important; color: {C['TEXT']} !important; border: 1px solid {C['BORDER']} !important; width: 100%; }}
        ul[role="listbox"], li[role="option"] {{ background-color: {C['SIDEBAR']} !important; color: {C['TEXT']} !important; }}
        hr {{ border-color: {C['BORDER']} !important; margin: 1.5rem 0 !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()

# --- 5. LÓGICA DE IMAGEM LOCAL ---
def get_image_base64(filepath):
    try:
        with open(filepath, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception: return None

def render_profile_header(nome, cargo, empresa, linkedin_url):
    img_html = ""
    if linkedin_url and linkedin_url != "#":
        parts = [p for p in linkedin_url.split('/') if p]
        if parts:
            link_id = parts[-1]
            filepath = f"sabi/{link_id}.png"
            if os.path.exists(filepath):
                b64 = get_image_base64(filepath)
                if b64:
                    img_html = f'<img src="data:image/png;base64,{b64}" class="profile-pic">'
    
    st.markdown(f"""
        <div class="profile-wrapper">
            {img_html}
            <div>
                <h1 style="margin-bottom:0;">{nome}</h1>
                <p class="subtext" style="font-size:1.2rem; margin:0;">{cargo} @ <strong>{empresa}</strong></p>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:2rem;">Intelligence CRM V4.0</p>', unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Corporate ID")
            p = st.text_input("Security Token", type="password")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(u, p): st.session_state.logado = True; st.rerun()
                else: st.error("Access Denied.")
    st.stop()

# --- 7. DATA ENGINE EXTREMO ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "score": 55, "linkedin": "https://www.linkedin.com/in/brunoszarf", "bio": "Executivo sênior focado em inovação global e gestão de performance.", "loc": "São Paulo, SP", "interesse": "IA, Transformação Digital"},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP Cultura", "decisor": "Sim", "score": 52, "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "bio": "Especialista em cultura organizacional e SSMA em multinacionais.", "loc": "Joinville, SC", "interesse": "ESG, Cultura Org"},
    {"id": 3, "nome": "Aldo Silva", "empresa": "HCOSTA", "cargo": "CHRO", "decisor": "Sim", "score": 50, "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353", "bio": "Líder de Gente & Gestão focado em otimização de equipes.", "loc": "Bauru, SP", "interesse": "Data-Driven HR"},
    {"id": 4, "nome": "Thais Ferreira", "empresa": "G5 Partners", "cargo": "VP People", "decisor": "Sim", "score": 49, "linkedin": "https://www.linkedin.com/in/thais-vendramini", "bio": "Gestão de talentos em M&A e mercados financeiros.", "loc": "São Paulo, SP", "interesse": "Retenção de Talentos"},
    {"id": 5, "nome": "Mari Stela", "empresa": "HILTI", "cargo": "CHRO", "decisor": "Sim", "score": 48, "linkedin": "https://www.linkedin.com/in/mariribeiro", "bio": "HR em indústria de alta tecnologia e construção.", "loc": "São Paulo, SP", "interesse": "Leadership Development"},
    {"id": 6, "nome": "Brenda Endo", "empresa": "Embracon", "cargo": "Diretora RH", "decisor": "Sim", "score": 47, "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041", "bio": "Diretora focada em bem-estar e consórcios.", "loc": "Campinas, SP", "interesse": "Employee Experience"},
    {"id": 7, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "decisor": "Parcial", "score": 46, "linkedin": "https://www.linkedin.com/in/sorayabahde", "bio": "Liderança executiva em grandes bancos.", "loc": "Osasco, SP", "interesse": "Inovação Financeira"},
    {"id": 8, "nome": "Ana Luiza Brasil", "empresa": "Fortbras", "cargo": "Dir. Gente", "decisor": "Sim", "score": 45, "linkedin": "https://www.linkedin.com/in/brasilana", "bio": "Gestão de pessoas no setor automotivo.", "loc": "São Paulo, SP", "interesse": "Integração Pós-M&A"},
    {"id": 9, "nome": "Patricia Bobbato", "empresa": "Natura", "cargo": "Dir. Cultura", "decisor": "Parcial", "score": 43, "linkedin": "https://www.linkedin.com/in/patriciabobbato", "bio": "Foco profundo em Diversidade, Equidade e Inclusão.", "loc": "São Paulo, SP", "interesse": "DE&I, Sustentabilidade"}
]

def calc_est(score):
    if score >= 48: return "Tier 1", "> R$ 1 MILHÃO", "pill-blue", 1500000
    if score >= 39: return "Tier 2", "R$ 500k - 1M", "pill-magenta", 750000
    return "Tier 3", "< R$ 500k", "pill-neutral", 250000

vol_total = 0
for l in LEADS_BASE:
    l['t'], l['o'], l['c'], val = calc_est(l['score'])
    vol_total += val

df_leads = pd.DataFrame(LEADS_BASE)

# --- 8. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("📊 Executive Dash", use_container_width=True, disabled=(st.session_state.view_mode=='dashboard')): st.session_state.view_mode='dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=(st.session_state.view_mode=='list')): st.session_state.view_mode='list'; st.rerun()
    st.divider()
    if st.button("🌓 Toggle Theme", use_container_width=True): st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()
    if st.button("🚪 Logout", use_container_width=True): st.session_state.logado = False; st.rerun()

# --- 9. VIEWS ---
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1>Executive Overview</h1>', unsafe_allow_html=True)
    
    # Macro Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Contas Estratégicas", len(df_leads))
    c2.metric("Decisores Mapeados", len(df_leads[df_leads['decisor'] == 'Sim']))
    c3.metric("Volume em Pipeline", f"> R$ {vol_total / 1000000:.1f}M")
    
    st.divider()
    font_col = "#ffffff" if st.session_state.theme == 'dark' else "#1A1A1C"
    
    st.markdown("### Distribuição Estratégica (Tiers)")
    fig_donut = px.pie(df_leads, names='t', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig_donut.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_col, margin=dict(l=0,r=0,t=10,b=0), height=350, showlegend=True, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_donut, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1>Strategic Pipeline</h1>', unsafe_allow_html=True)
    sel = st.selectbox("Filtrar Classe", ["Todos", "Tier 1", "Tier 2", "Tier 3"])
    f_leads = LEADS_BASE if sel == "Todos" else [l for l in LEADS_BASE if sel in l['t']]
    st.write("")
    
    for l in f_leads:
        bg = "rgba(255, 255, 255, 0.02)" if st.session_state.theme == 'dark' else "#FFFFFF"
        bd = "rgba(255, 255, 255, 0.08)" if st.session_state.theme == 'dark' else "#D1D1D6"
        card = f"""<div style="background:{bg}; border:1px solid {bd}; border-radius:12px; padding:1rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
            <div><strong style="font-size: 1.1rem;">{l['nome']}</strong><br><span class="subtext">{l['cargo']}</span></div>
            <div style="text-align:right;"><span class="{l['c']}">{l['t']}</span></div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items: center; border-top: 1px solid {bd}; padding-top: 8px;">
            <span style="font-weight: 500;">{l['empresa']}</span>
            <span class="{l['c']}">{l['o']}</span>
        </div></div>"""
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Analisar Perfil", key=f"b_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']; st.session_state.view_mode = 'detail'; st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['id'] == st.session_state.selected_lead_id)
    if st.button("← Voltar ao Funil", use_container_width=True): st.session_state.view_mode = 'list'; st.rerun()
    
    st.write("")
    render_profile_header(l['nome'], l['cargo'], l['empresa'], l.get('linkedin', '#'))
    
    # --- GRID 2x2 ELÁSTICO & POTENCIAL REFINADO ---
    c1, c2 = st.columns(2)
    c1.metric("Classificação", l['t'])
    c2.metric("Score", f"{l['score']} pts")
    
    c3, c4 = st.columns(2)
    c3.metric("Decisor", l['decisor'])
    with c4:
        st.markdown(f"""
            <div class="potencial-wrapper">
                <span class="subtext" style="font-size: 0.8rem; text-transform: uppercase; font-weight: 600; margin-bottom: 5px;">Potencial Est.</span>
                <p class="potencial-val">{l['o']}</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    
    # --- EXPANSOR HIGH-END ---
    with st.expander("📂 Expandir Detalhes Estratégicos"):
        ec1, ec2 = st.columns(2)
        ec1.markdown(f"**📍 Localização:** {l.get('loc', 'N/I')}")
        ec1.markdown(f"**🎯 Interesses:** {l.get('interesse', 'N/I')}")
        ec2.markdown(f"**📝 Bio/Briefing:** {l.get('bio', 'N/I')}")
        if l.get('linkedin') and l['linkedin'] != "#": st.link_button("Abrir LinkedIn", l['linkedin'])
    
    st.divider()
    
    # --- REGISTRO & TIMELINE (COM PERSISTÊNCIA FÍSICA) ---
    st.markdown("### Registro")
    st.markdown("<p class='subtext' style='font-size: 0.9rem;'>Adicionar Novo Registro</p>", unsafe_allow_html=True)
    
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota:", placeholder="Descreva os próximos passos ou insights do contato...", label_visibility="collapsed")
        
        if st.form_submit_button("Salvar Nota", type="primary", use_container_width=True):
            if txt.strip():
                # Adiciona no topo da lista
                nova_nota = {
                    "id_lead": l['id'], 
                    "dt": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                    "txt": txt
                }
                st.session_state.notas_locais.insert(0, nova_nota)
                # Salva no arquivo físico instantaneamente
                save_notes(st.session_state.notas_locais)
                st.rerun()
    
    st.write("")
    
    notas = [x for x in st.session_state.notas_locais if x.get('id_lead') == l['id']]
    if not notas:
        st.info("Nenhum log registrado para esta conta.")
    else:
        for n in notas:
            st.markdown(f"""
            <div style="padding-left: 10px;">
                <div class="chat-bubble">
                    <div style="font-size: 0.75rem; color: #8E8E93; font-weight: 600; margin-bottom: 5px;">{n['dt']}</div>
                    <p style="margin: 0; line-height: 1.4; font-size: 0.95rem;">{n['txt']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
