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

        /* UX de Input (100% Contraste Modo Claro) */
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

        /* Fotos Circulares */
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

        /* Grid 2x2 Elástico */
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
            font-size: 1.8rem; font-weight: 800; margin: 0; letter-spacing: -0.5px; 
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}

        /* Timeline Premium */
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

# --- 7. DATA ENGINE REAL (MOCK) ---
LEADS_BASE = [
    {
        'id': 17, 'nome': 'Camila Alves Massaro', 'empresa': 'ArcelorMittal Gonvarri', 
        'cargo': 'Director of People, Strategy & IT', 'decisor': 'Sim', 'score': 58, 
        'linkedin': 'https://www.linkedin.com/in/camilamassaro-rh', 
        'bio': 'Processamento e distribuição de aço.', 
        'interesse': 'Novos Modelos de Trabalho, Automação de Processos no RH, Gestão da Mudança, Cultura Organizacional', 
        'desafios': 'Retenção de Talentos e Rotatividade (Turnover), Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida...', 
        'orcamento_real': 'De 50 milhões até 100 milhões', 'receita': 'Acima de 1bilhao', 
        'funcionarios': 'De 500 a 1000 funcionários', 'prazo': '13 - 18 meses', 
        'solucao': 'Gestão de Mudança e Cultura Organizacional', 
        'comentarios_caio': 'Temos contato, fizemos várias propostas negadas mas nunca foi vendido.'
    },
    {
        'id': 1, 'nome': 'Bruno Szarf', 'empresa': 'Stefanini', 'cargo': 'VP Global', 'decisor': 'Sim', 'score': 56, 
        'linkedin': 'https://www.linkedin.com/in/brunoszarf', 'bio': 'Consultoria e soluções em TI.', 
        'interesse': 'Treinamento e Desenvolvimento, Aquisição e Retenção de Talentos', 
        'desafios': 'Desenvolvimento de Lideranças, Adoção e Integração de IA', 
        'orcamento_real': 'De 10 milhões até 50 milhões', 'receita': 'Acima de 1bilhao', 
        'funcionarios': 'Acima de 10000', 'prazo': '4 - 6 meses', 'solucao': '-', 'comentarios_caio': ''
    },
    {
        'id': 2, 'nome': 'Brenda Donato Endo', 'empresa': 'Embracon', 'cargo': 'Diretora de RH', 'decisor': 'Sim', 'score': 56, 
        'linkedin': 'https://www.linkedin.com/in/brenda-donato-endo-78275041', 'bio': 'Administradora de consórcios de bens.', 
        'interesse': 'Treinamento e Desenvolvimento, Novos Modelos de Trabalho', 
        'desafios': 'Saúde Mental e Bem-Estar, Gestão da Cultura Híbrida', 
        'orcamento_real': 'De 10 milhões até 50 milhões', 'receita': 'Acima de 1bilhao', 
        'funcionarios': 'De 1000 a 5000 funcionários', 'prazo': '0 - 3 meses', 'solucao': '-', 'comentarios_caio': ''
    }
]

def calc_meta(score):
    if score >= 48: return "Tier 1", "> R$ 1 Milhão", "pill-blue", 1500000
    if score >= 39: return "Tier 2", "R$ 500k - 1M", "pill-magenta", 750000
    return "Tier 3", "< R$ 500k", "pill-neutral", 250000

vol_total = 0
for l in LEADS_BASE:
    l['t'], l['o'], l['c'], val = calc_meta(l['score'])
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
    
    # Grid 2x2
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Classificação</p><p class="metric-value">{l["t"]}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Score</p><p class="metric-value">{l["score"]} pts</p></div>', unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    with c3: st.markdown(f'<div class="custom-metric-card"><p class="metric-label">Decisor</p><p class="metric-value">{l["decisor"]}</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="potencial-wrapper"><p class="metric-label" style="color:#8E8E93;">Potencial Est.</p><p class="potencial-val">{l["o"]}</p></div>', unsafe_allow_html=True)
    
    st.write("")
    
    # Dossiê Expandido
    with st.expander("📂 Visualizar Dossiê Completo"):
        ec1, ec2 = st.columns(2)
        ec1.markdown(f"**🏢 Receita:** {l.get('receita', 'N/I')}\n\n**👥 Funcionários:** {l.get('funcionarios', 'N/I')}\n\n**🎯 Desafios:** {l.get('desafios', 'N/I')}")
        ec2.markdown(f"**⏳ Prazo Investimento:** {l.get('prazo', 'N/I')}\n\n**🛠 Solução Desejada:** {l.get('solucao', 'N/I')}\n\n**💡 Interesses:** {l.get('interesse', 'N/I')}")
        if l.get('comentarios_caio'):
            st.markdown(f"**💬 Comentários Internos:** {l['comentarios_caio']}")
        if l.get('linkedin') and l['linkedin'] != "#": st.link_button("Abrir LinkedIn", l['linkedin'])

    st.divider()
    
    # Timeline de Interações
    st.markdown("### Registro")
    
    with st.form("intel_form", clear_on_submit=True):
        txt = st.text_area("Nota", placeholder="Descreva a interação ou novos insights...", label_visibility="collapsed")
        
        # Audio input support
        audio_val = None
        if hasattr(st, 'audio_input'):
            audio_val = st.audio_input("Gravar Voice Note (Opcional)")
        elif hasattr(st, 'experimental_audio_input'):
            audio_val = st.experimental_audio_input("Gravar Voice Note (Opcional)")

        if st.form_submit_button("Registrar Insight", type="primary", use_container_width=True):
            if txt.strip() or audio_val is not None:
                audio_url = None
                if audio_val is not None:
                    lid_safe = extract_linkedin_id(l['linkedin']) or str(l['id'])
                    audio_url = upload_audio_to_supabase(audio_val.read(), lid_safe)
                
                save_note_to_supabase(extract_linkedin_id(l['linkedin']) or str(l['id']), txt.strip(), audio_url)
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
            
            # Use native Streamlit audio component to prevent base64 size limits & take advantage of Supabase public URLs
            if n.get('audio_url'):
                st.audio(n['audio_url'])
