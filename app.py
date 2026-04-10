import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Artefact | Strategy",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'

# --- 3. ENGINE DE DESIGN (CSS PREMIUM) ---
def apply_theme():
    is_dark = st.session_state.theme == 'dark'
    
    # Paleta Dinâmica C-Level
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

        /* Cartões de Métrica */
        div[data-testid="stMetric"] {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 1.5rem !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.02);
        }}

        /* Linhas da Tabela (Leads) */
        .lead-row {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 0.5rem;
            transition: all 0.2s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.01);
        }}
        .lead-row:hover {{
            background: {row_hover};
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0,0,0,0.05);
        }}
        
        .tier-1-bar {{
            height: 4px; width: 100%;
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            border-radius: 8px 8px 0 0;
            margin-bottom: -4px;
        }}

        /* Botões Premium */
        .stButton>button {{
            border-radius: 8px !important;
            border: 1px solid {card_border} !important;
            background-color: {btn_bg} !important;
            color: {text_color} !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }}
        .stButton>button:hover {{
            border-color: #3232ff !important;
            box-shadow: 0 4px 12px rgba(50, 50, 255, 0.15) !important;
            transform: translateY(-1px) !important;
        }}
        /* Botão Primário (Azul/Magenta) */
        .stButton>button[kind="primary"] {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important;
            color: #ffffff !important;
            border: none !important;
        }}

        /* Pills de Status */
        .pill-blue {{ color: #3232ff; font-weight: 600; }}
        .pill-magenta {{ color: #ff1493; font-weight: 600; }}
        .pill-neutral {{ color: {sub_text}; font-weight: 500; }}

        hr {{ border-color: {card_border} !important; margin: 2rem 0 !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_theme()

# --- 4. SISTEMA DE AUTENTICAÇÃO ---
def check_login(user, pwd):
    val_user = st.secrets.get("APP_USER", "admin")
    val_pass = st.secrets.get("APP_PASS", "datilografia")
    return hmac.compare_digest(user, val_user) and hmac.compare_digest(pwd, val_pass)

# --- 5. TELA DE LOGIN ---
if not st.session_state.logado:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.write("\n" * 5)
        st.markdown('<h1 class="atf-gradient" style="font-size:3.5rem; text-align:center; margin-bottom:0;">Artefact</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtext" style="text-align:center; margin-bottom:3rem; font-size:1.1rem;">Executive Intelligence</p>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            st.write("")
            if st.form_submit_button("Acessar Plataforma", use_container_width=True, type="primary"):
                if check_login(user_input, pass_input):
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Acesso negado.")
    st.stop()

# --- 6. DADOS COMPLETOS (40 LEADS) ---
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

# --- 7. MENU LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient" style="font-size:2.2rem; margin-bottom:0;">Artefact</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtext" style="margin-bottom:2rem; font-weight:500;">Intelligence CRM</p>', unsafe_allow_html=True)
    
    is_dash = st.session_state.view_mode == 'dashboard'
    is_pipe = st.session_state.view_mode == 'list'
    
    if st.button("📊 Dashboard Executivo", use_container_width=True, disabled=is_dash):
        st.session_state.view_mode = 'dashboard'
        st.rerun()
        
    if st.button("👥 Pipeline de Leads", use_container_width=True, disabled=is_pipe):
        st.session_state.view_mode = 'list'
        st.rerun()
        
    st.divider()
    
    tema_atual = "🌙 Modo Escuro" if st.session_state.theme == 'dark' else "☀️ Modo Claro"
    if st.button(f"Alternar Tema ({tema_atual})", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()

    st.divider()
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

# --- 8. RENDERIZAÇÃO DA TELA PRINCIPAL ---

# MODO: DASHBOARD
if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1 style="margin-bottom:0;">Visão Executiva</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtext" style="font-size:1.1rem;">Panorama de contas estratégicas e status de funil.</p>', unsafe_allow_html=True)
    st.write("")
    
    # 4 Métricas Macro
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Contas", len(df_leads))
    c2.metric("Contas Tier 1", len(df_leads[df_leads['tier'].str.contains('Tier 1')]))
    c3.metric("Contas Tier 2", len(df_leads[df_leads['tier'].str.contains('Tier 2')]))
    c4.metric("Decisores Claros", len(df_leads[df_leads['decisor'] == 'Sim']))
    
    st.divider()
    
    # Cores dinâmicas para os gráficos (suporta dark/light mode)
    font_color = "#ffffff" if st.session_state.theme == 'dark' else "#111111"
    
    # Gráficos
    g1, g2 = st.columns([2, 1.5])
    
    with g1:
        st.markdown("<h3 style='font-size:1.1rem; font-weight:600;'>Distribuição por Nível de Conta (Tier)</h3>", unsafe_allow_html=True)
        tier_counts = df_leads['tier'].value_counts().reset_index()
        tier_counts.columns = ['Tier', 'Volume']
        fig1 = px.bar(tier_counts, x='Volume', y='Tier', orientation='h', color='Tier',
                     color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color,
            showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), margin=dict(l=0, r=0, t=20, b=0), height=300
        )
        st.plotly_chart(fig1, use_container_width=True)
        
    with g2:
        st.markdown("<h3 style='font-size:1.1rem; font-weight:600;'>Potencial de Orçamento</h3>", unsafe_allow_html=True)
        bud_counts = df_leads['orcamento'].value_counts().reset_index()
        bud_counts.columns = ['Orçamento', 'Volume']
        fig2 = px.pie(bud_counts, values='Volume', names='Orçamento', hole=0.7,
                      color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color,
            margin=dict(l=0, r=0, t=20, b=0), height=300,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig2, use_container_width=True)

# MODO: LISTA DE LEADS
elif st.session_state.view_mode == 'list':
    st.markdown('<h1 style="margin-bottom:0;">Pipeline de Lideranças</h1>', unsafe_allow_html=True)
    st.write("")
    
    # Tabela (Cabeçalho)
    h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
    h1.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">EXECUTIVO</span>', unsafe_allow_html=True)
    h2.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">EMPRESA</span>', unsafe_allow_html=True)
    h3.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">CLASSIFICAÇÃO</span>', unsafe_allow_html=True)
    h4.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">ORÇAMENTO</span>', unsafe_allow_html=True)
    st.markdown("<hr style='margin: 1rem 0 !important;'>", unsafe_allow_html=True)
    
    # Filtro rápido
    tier_filter = st.selectbox("Filtrar visualização por Tier", ["Todos", "Tier 1 - Strategic", "Tier 2 - High Priority", "Tier 3 - Nurturing"])
    leads_filtrados = LEADS_BASE if tier_filter == "Todos" else [l for l in LEADS_BASE if l['tier'] == tier_filter]
    
    for l in leads_filtrados:
        if "Tier 1" in l['tier']:
            tier_class, budget_class, grad_bar = "pill-blue", "pill-blue", '<div class="tier-1-bar"></div>'
        elif "Tier 2" in l['tier']:
            tier_class, budget_class, grad_bar = "pill-magenta", "pill-magenta", ''
        else:
            tier_class, budget_class, grad_bar = "pill-neutral", "pill-neutral", ''

        st.markdown(f"""
        <div class="lead-row">
            {grad_bar}
            <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 5px;">
                <div style="flex: 3;">
                    <strong style="font-size: 1.1rem;">{l['nome']}</strong><br>
                    <span class="subtext" style="font-size: 0.9rem;">{l['cargo']}</span>
                </div>
                <div style="flex: 2; font-weight: 500;">{l['empresa']}</div>
                <div style="flex: 2;"><span class="{tier_class}">{l['tier']}</span></div>
                <div style="flex: 2;"><span class="{budget_class}">{l['orcamento']}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        _, btn_col = st.columns([9, 1])
        with btn_col:
            if st.button("Abrir", key=f"btn_{l['id']}", use_container_width=True):
                st.session_state.selected_lead_id = l['id']
                st.session_state.view_mode = 'detail'
                st.rerun()

# MODO: DETALHES DO LEAD
elif st.session_state.view_mode == 'detail':
    lead = next(l for l in LEADS_BASE if l['id'] == st.session_state.selected_lead_id)
    
    if st.button("← Voltar ao Pipeline"):
        st.session_state.view_mode = 'list'
        st.rerun()
        
    st.write("")
    
    c_info, c_action = st.columns([6, 2])
    with c_info:
        st.markdown(f"<h1 style='margin-bottom:0; font-size: 2.5rem;'>{lead['nome']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='subtext' style='font-size:1.2rem; font-weight:500;'>{lead['cargo']} @ <strong>{lead['empresa']}</strong></p>", unsafe_allow_html=True)
    with c_action:
        if lead['linkedin'] != "#":
            st.link_button("↗ Perfil LinkedIn", lead['linkedin'], use_container_width=True)
            
    st.divider()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Classificação", lead['tier'].split(" - ")[0])
    m2.metric("Score de Mapeamento", f"{lead['score']} pts")
    m3.metric("Poder de Decisão", lead['decisor'])
    m4.metric("Potencial", lead['orcamento'])
    
    st.divider()
    
    st.markdown("### Histórico e Inteligência")
    st.info("Interface pronta. Integração com GitHub comentada no código para você ativar quando quiser.")
    
    nova_nota = st.text_area("Adicionar novo insight para " + lead['nome'])
    if st.button("Salvar Registro", type="primary"):
        st.success("Nota salva com sucesso! (Simulação)")
