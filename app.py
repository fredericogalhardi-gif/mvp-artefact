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
    initial_sidebar_state="collapsed" # Começa fechado para focar no conteúdo no celular
)

# --- 2. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'notas_locais' not in st.session_state: st.session_state.notas_locais = []

# --- 3. ENGINE DE DESIGN (CSS MOBILE & ADAPTIVE THEME) ---
def apply_theme():
    is_dark = st.session_state.theme == 'dark'
    
    bg_color = "#0A0A0F" if is_dark else "#F7F8FA"
    sidebar_bg = "#111116" if is_dark else "#FFFFFF"
    text_color = "#FFFFFF" if is_dark else "#111111"
    sub_text = "#888890" if is_dark else "#666666"
    card_bg = "rgba(255, 255, 255, 0.03)" if is_dark else "#FFFFFF"
    card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
    row_hover = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.02)"
    btn_bg = "transparent" if is_dark else "#FFFFFF"
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;800&display=swap');
        
        /* Backgrounds Principais */
        .stApp {{ background-color: {bg_color}; font-family: 'Inter', sans-serif; color: {text_color}; }}
        [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {card_border}; }}
        [data-testid="stHeader"] {{ background-color: transparent !important; }}
        
        h1, h2, h3, p, span {{ color: {text_color} !important; }}
        .subtext {{ color: {sub_text} !important; }}

        /* Artefact Gradient */
        .atf-gradient {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* Filtro Selectbox Adaptativo (Correção Tema Claro) */
        div[data-baseweb="select"] > div {{
            background-color: {card_bg} !important;
            border-color: {card_border} !important;
            color: {text_color} !important;
        }}
        div[data-baseweb="select"] span {{ color: {text_color} !important; }}
        ul[role="listbox"], ul[role="listbox"] li {{
            background-color: {sidebar_bg} !important;
            color: {text_color} !important;
        }}

        /* Cartões de Métrica (Ajuste para Mobile) */
        div[data-testid="stMetric"] {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 1rem !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.02);
        }}
        div[data-testid="stMetricValue"] > div {{
            font-size: 1.5rem !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }}

        /* Cartões de Leads Mobile-First */
        .lead-row {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            transition: all 0.2s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.01);
            position: relative;
            overflow: hidden;
        }}
        .lead-row:hover {{
            background: {row_hover};
            transform: translateY(-2px);
        }}
        .tier-1-bar {{
            position: absolute; top: 0; left: 0;
            height: 4px; width: 100%;
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
        }}

        /* Botões Premium */
        .stButton>button {{
            border-radius: 8px !important;
            border: 1px solid {card_border} !important;
            background-color: {btn_bg} !important;
            color: {text_color} !important;
            font-weight: 500 !important;
            padding: 0.5rem !important;
            transition: all 0.3s ease !important;
        }}
        .stButton>button:hover {{ border-color: #3232ff !important; box-shadow: 0 4px 12px rgba(50, 50, 255, 0.15) !important; }}
        .stButton>button[kind="primary"] {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important;
            color: #ffffff !important; border: none !important;
        }}

        /* Pills */
        .pill-blue {{ color: #3232ff; font-weight: 600; }}
        .pill-magenta {{ color: #ff1493; font-weight: 600; }}
        .pill-neutral {{ color: {sub_text}; font-weight: 500; }}

        hr {{ border-color: {card_border} !important; margin: 1.5rem 0 !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_theme()

# --- 4. SISTEMA DE AUTENTICAÇÃO (UTF-8 SEGURO) ---
def check_login(user, pwd):
    try:
        val_user = st.secrets["APP_USER"]
        val_pass = st.secrets["APP_PASS"]
        return hmac.compare_digest(user.encode('utf-8'), val_user.encode('utf-8')) and \
               hmac.compare_digest(pwd.encode('utf-8'), val_pass.encode('utf-8'))
    except KeyError:
        st.error("Erro: Credenciais não configuradas nos Secrets.")
        return False

# --- 5. TELA DE LOGIN ---
if not st.session_state.logado:
    st.write("\n" * 3)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<h1 class="atf-gradient" style="font-size:3rem; text-align:center; margin-bottom:0;">Artefact</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:2rem;">Strategy Intelligence</p>', unsafe_allow_html=True)
        with st.form("login_form"):
            user_input = st.text_input("Corporate ID")
            pass_input = st.text_input("Token", type="password")
            st.write("")
            if st.form_submit_button("Authenticate", use_container_width=True, type="primary"):
                if check_login(user_input, pass_input):
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("Acesso Negado.")
    st.stop()

# --- 6. DADOS COMPLETOS (40 LEADS) E LÓGICA ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf", "score": 55},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP de Pessoas, Cultura e SSMA", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "score": 52},
    {"id": 3, "nome": "Aldo Silva dos Santos", "empresa": "HCOSTA", "cargo": "CHRO Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/", "score": 50},
    {"id": 4, "nome": "Thais C. A. V. Ferreira", "empresa": "G5 Partners", "cargo": "VP - People & Culture", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/thais-vendramini/", "score": 49},
    {"id": 5, "nome": "Mari Stela Ribeiro", "empresa": "HILTI do Brasil", "cargo": "CHRO", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/mariribeiro", "score": 48},
    {"id": 6, "nome": "Brenda Donato Endo", "empresa": "Embracon", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041", "score": 47},
    {"id": 7, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/sorayabahde", "score": 46},
    {"id": 8, "nome": "Ana Luiza G. Brasil", "empresa": "Fortbras", "cargo": "Diretor de Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brasilana", "score": 45},
    {"id": 9, "nome": "Daniela Matos Faria", "empresa": "Zamp", "cargo": "Diretora de Talentos e Cultura", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-matos-faria", "score": 44},
    {"id": 10, "nome": "Patricia Bobbato", "empresa": "Natura", "cargo": "Diretora de Cultura e DE&I", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/patriciabobbato", "score": 43},
    {"id": 11, "nome": "Juliana Dorigo", "empresa": "Grupo Ecoagro", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/julianadorigorh", "score": 42},
    {"id": 12, "nome": "Daniela Nishimoto", "empresa": "Grupo L'Oréal", "cargo": "Diretora Relações Humanas", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1", "score": 41},
    {"id": 13, "nome": "Danila Pires Carsoso", "empresa": "Motiva", "cargo": "Diretor", "decisor": "Não", "linkedin": "#", "score": 40},
    {"id": 14, "nome": "RITA SOUZA", "empresa": "Bunge Alimentos", "cargo": "Diretora Gestão Mudança Org", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/rita-souza-neurochange/", "score": 39},
    {"id": 15, "nome": "GIOVANI CARRA", "empresa": "ADF ONDULADOS", "cargo": "DIRETOR DE RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/giovani-carra-65858a33", "score": 38},
    {"id": 16, "nome": "Gerson Cosme santos", "empresa": "GHT", "cargo": "Diretor gente & performance", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/gerson-cosme-santos", "score": 37},
    {"id": 17, "nome": "Neto Mello", "empresa": "Adimax", "cargo": "Diretor de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/netomello", "score": 36},
    {"id": 18, "nome": "Camila Alves Massaro", "empresa": "ArcelorMittal", "cargo": "Director of People", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/camilamassaro-rh", "score": 35},
    {"id": 19, "nome": "Willian Souza", "empresa": "EMS", "cargo": "Diretor de Treinamento", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/willian-souza-63874147", "score": 34},
    {"id": 20, "nome": "Angelo Fanti", "empresa": "Sorocaba Refrescos S/A", "cargo": "Diretor Recursos Humanos", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/angelo-fanti-58a4a821", "score": 33},
    {"id": 21, "nome": "Daniela Monteiro", "empresa": "Editora do Brasil", "cargo": "Diretora de RH & Marca", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/daniela-monteiro-a3125970", "score": 32},
    {"id": 22, "nome": "Mario Felicio Neto", "empresa": "CPQD", "cargo": "Diretor de Gente e gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/mario-felicio-neto", "score": 31},
    {"id": 23, "nome": "Frederico C. Neto", "empresa": "Afya", "cargo": "Diretor de Recursos Humanos", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/frederico-cosentino-b67b1a20", "score": 30},
    {"id": 24, "nome": "Tâmara Costa", "empresa": "SantoDigital", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/tamiscosta", "score": 29},
    {"id": 25, "nome": "Diná R. de Carvalho", "empresa": "Superlógica", "cargo": "Diretora de Gente e Gestão", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/diná-ribeiro-de-carvalho-a1a184348", "score": 28},
    {"id": 26, "nome": "Alisson Gratão", "empresa": "Copagril", "cargo": "Superintendente de Gestão", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/alisson1", "score": 27},
    {"id": 27, "nome": "Lenita David G. P. Freitas", "empresa": "Flora Produtos", "cargo": "Gerente executiva de RH", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/lenita-gilioli-freitas", "score": 26},
    {"id": 28, "nome": "Daniel Peruchi", "empresa": "Alcoa", "cargo": "Gerente Sênior RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9", "score": 25},
    {"id": 29, "nome": "Thamires C. A. P. Justino", "empresa": "Alcoa Alumínio", "cargo": "Gerente de RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/thamires-pedro-15287611b/", "score": 24},
    {"id": 30, "nome": "Ariana Tertuliano", "empresa": "Casa do Construtor", "cargo": "Gerente de RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/ariana-tertuliano-81a65538", "score": 23},
    {"id": 31, "nome": "Ricardo Malvestite", "empresa": "GBMX", "cargo": "Gerente Sr RH", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/ricardo-malvestite-74b1936", "score": 22},
    {"id": 32, "nome": "Sabrina G. R. Lemes", "empresa": "GBMX", "cargo": "Gerente EHS", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107", "score": 21},
    {"id": 33, "nome": "Jader Éder Bleil", "empresa": "Greenbrier Maxion", "cargo": "Gerente de Relações Trab.", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225", "score": 20},
    {"id": 34, "nome": "ANDRE L. E. ARANHA", "empresa": "SUPERLOGICA", "cargo": "GERENTE DE REMUNERAÇÃO", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/andrelearanha", "score": 19},
    {"id": 35, "nome": "Nelson Simeoni Junior", "empresa": "Superlógica", "cargo": "Gerente de DHO", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/nelsonsimeoni", "score": 18},
    {"id": 36, "nome": "Caroline Faki de Miranda", "empresa": "Vigor Alimentos", "cargo": "Head de Business Partner", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/caroline-faki-68338285", "score": 17},
    {"id": 37, "nome": "Marcelo Carlos Pinheiro", "empresa": "Greenbrier Maxion", "cargo": "Gerente Senior", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/marcelo-pinheiro-274abb24", "score": 16},
    {"id": 38, "nome": "Jader Eder Bleil", "empresa": "Greenbrier Maxion", "cargo": "Gerente RT", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225", "score": 15},
    {"id": 39, "nome": "Michele Ferreira", "empresa": "Confiança Supermercados", "cargo": "Coordenadora de DHO", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/michele-ferreira-16401083", "score": 14},
    {"id": 40, "nome": "Frederico Galhardi Borges", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "#", "score": 13}
]

def classificar_tier(score):
    if score >= 48: return "Tier 1 - Strategic"
    elif score >= 39: return "Tier 2 - High Priority"
    else: return "Tier 3 - Nurturing"

def estimar_orcamento(tier):
    if "Tier 1" in tier: return "> R$ 1 Milhão"
    elif "Tier 2" in tier: return "R$ 500k - R$ 1M"
    else: return "< R$ 500k"

for lead in LEADS_BASE:
    lead['tier'] = classificar_tier(lead.get('score', 0))
    lead['orcamento'] = estimar_orcamento(lead['tier'])

df_leads = pd.DataFrame(LEADS_BASE)

# --- 7. MENU LATERAL ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient" style="font-size:2rem; margin-bottom:0;">Artefact</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtext" style="margin-bottom:2rem; font-weight:500;">Intelligence CRM</p>', unsafe_allow_html=True)
    
    is_dash = st.session_state.view_mode == 'dashboard'
    is_pipe = st.session_state.view_mode == 'list'
    
    if st.button("📊 Overview", use_container_width=True, disabled=is_dash):
        st.session_state.view_mode = 'dashboard'; st.rerun()
    if st.button("👥 Pipeline", use_container_width=True, disabled=is_pipe):
        st.session_state.view_mode = 'list'; st.rerun()
        
    st.divider()
    tema_atual = "🌙 Midnight" if st.session_state.theme == 'dark' else "☀️ Platinum"
    if st.button(f"Tema: {tema_atual}", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'; st.rerun()

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logado = False; st.rerun()

# --- 8. RENDERIZAÇÃO PRINCIPAL ---

# MODO: DASHBOARD
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h2 style="margin-bottom:0;">Visão Executiva</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtext">Panorama do Funil</p>', unsafe_allow_html=True)
    
    # Métricas adaptadas para Mobile (Usando 2 colunas para não espremer)
    m1, m2 = st.columns(2)
    m1.metric("Contas Totais", len(df_leads))
    m2.metric("Decisores", len(df_leads[df_leads['decisor'] == 'Sim']))
    
    m3, m4 = st.columns(2)
    m3.metric("Contas Tier 1", len(df_leads[df_leads['tier'].str.contains('Tier 1')]))
    m4.metric("Contas Tier 2", len(df_leads[df_leads['tier'].str.contains('Tier 2')]))
    
    st.divider()
    
    font_color = "#ffffff" if st.session_state.theme == 'dark' else "#111111"
    
    # Gráficos empilhados para responsividade
    st.markdown("### Distribuição de Classes")
    fig1 = px.bar(df_leads['tier'].value_counts().reset_index(), x='count', y='tier', orientation='h', color='tier', color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), margin=dict(l=0, r=0, t=10, b=0), height=250)
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### Potencial de Orçamento")
    fig2 = px.pie(df_leads['orcamento'].value_counts().reset_index(), values='count', names='orcamento', hole=0.7, color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color, margin=dict(l=0, r=0, t=10, b=0), height=250, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig2, use_container_width=True)

# MODO: LISTA DE LEADS (CARTÕES MOBILE-FIRST)
elif st.session_state.view_mode == 'list':
    st.markdown('<h2 style="margin-bottom:0;">Pipeline</h2>', unsafe_allow_html=True)
    st.write("")
    
    # Filtro adaptativo
    tier_filter = st.selectbox("Filtrar Classe", ["Todos", "Tier 1 - Strategic", "Tier 2 - High Priority", "Tier 3 - Nurturing"])
    st.write("")
    
    leads_filtrados = LEADS_BASE if tier_filter == "Todos" else [l for l in LEADS_BASE if l['tier'] == tier_filter]
    
    for l in leads_filtrados:
        if "Tier 1" in l['tier']:
            t_class, b_class, bar = "pill-blue", "pill-blue", '<div class="tier-1-bar"></div>'
        elif "Tier 2" in l['tier']:
            t_class, b_class, bar = "pill-magenta", "pill-magenta", ''
        else:
            t_class, b_class, bar = "pill-neutral", "pill-neutral", ''

        # HTML do Cartão (Estrutura Vertical Mobile-Friendly - Colado na margem)
        html_card = f"""<div class="lead-row">
{bar}
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
    <div>
        <strong style="font-size: 1.1rem;">{l['nome']}</strong><br>
        <span class="subtext" style="font-size: 0.85rem;">{l['cargo']}</span>
    </div>
    <div style="text-align: right;">
        <span class="{t_class}" style="font-size: 0.85rem;">{l['tier'].split(' - ')[0]}</span>
    </div>
</div>
<div style="display: flex; justify-content: space-between; align-items: center;">
    <span style="font-size: 0.9rem; font-weight: 500;">{l['empresa']}</span>
    <span class="{b_class}" style="font-size: 0.9rem;">{l['orcamento']}</span>
</div>
</div>"""
        
        st.markdown(html_card, unsafe_allow_html=True)
        if st.button(f"Abrir Perfil", key=f"btn_{l['id']}", use_container_width=True):
            st.session_state.selected_lead_id = l['id']
            st.session_state.view_mode = 'detail'
            st.rerun()
        st.write("") # Espaço entre cartões e botões

# MODO: DETALHES DO LEAD (COM NOTAS)
elif st.session_state.view_mode == 'detail':
    lead = next(l for l in LEADS_BASE if l['id'] == st.session_state.selected_lead_id)
    
    if st.button("← Voltar ao Pipeline"):
        st.session_state.view_mode = 'list'
        st.rerun()
        
    st.write("")
    st.markdown(f"<h2 style='margin-bottom:0;'>{lead['nome']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p class='subtext' style='font-size:1.1rem;'>{lead['cargo']} @ <strong>{lead['empresa']}</strong></p>", unsafe_allow_html=True)
    
    if lead['linkedin'] != "#":
        st.link_button("↗ Abrir LinkedIn", lead['linkedin'])
            
    st.divider()
    
    # Métricas Empilhadas 2 a 2 para Celular
    m1, m2 = st.columns(2)
    m1.metric("Classificação", lead['tier'].split(" - ")[0])
    m2.metric("Score", f"{lead['score']} pts")
    
    m3, m4 = st.columns(2)
    m3.metric("Decisor", lead['decisor'])
    m4.metric("Potencial", lead['orcamento'])
    
    st.divider()
    
    st.markdown("### Inteligência")
    
    # Formulário de Notas (Limpa ao enviar)
    with st.form("nota_form", clear_on_submit=True):
        nova_nota = st.text_area("Adicionar novo insight estratégico:")
        submit = st.form_submit_button("Salvar Registro", use_container_width=True, type="primary")
        
        if submit and nova_nota.strip():
            st.session_state.notas_locais.insert(0, {
                "id_lead": lead['id'],
                "data": datetime.now().strftime("%d/%m/%Y às %H:%M"),
                "texto": nova_nota
            })
            st.rerun()
            
    st.markdown("#### Linha do Tempo")
    historico = [n for n in st.session_state.notas_locais if n['id_lead'] == lead['id']]
    
    if not historico:
        st.info("Nenhuma interação registrada para este executivo.")
    else:
        bg = "rgba(255,255,255,0.03)" if st.session_state.theme == 'dark' else "#F7F8FA"
        bd = "rgba(255,255,255,0.08)" if st.session_state.theme == 'dark' else "rgba(0,0,0,0.08)"
        
        for n in historico:
            st.markdown(f"""
            <div style="background:{bg}; border:1px solid {bd}; border-radius:8px; padding:1rem; margin-bottom:0.8rem;">
                <span class="subtext" style="font-size:0.75rem; font-weight:600; text-transform:uppercase;">📅 {n['data']}</span>
                <p style="margin-top:0.5rem; margin-bottom:0; font-size:0.95rem;">{n['texto']}</p>
            </div>
            """, unsafe_allow_html=True)
