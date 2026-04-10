import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Artefact | Strategy",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONTROLE DE SESSÃO (STATE) ---
if 'logado' not in st.session_state: st.session_state.logado = True # Deixei True para facilitar seus testes
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'dashboard'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'

# --- 3. ENGINE DE DESIGN (DYNAMIC CSS) ---
def apply_theme():
    is_dark = st.session_state.theme == 'dark'
    
    # Paleta Artefact
    bg_color = "#08080a" if is_dark else "#f4f5f7"
    text_color = "#ffffff" if is_dark else "#111111"
    sub_text = "#888890" if is_dark else "#666666"
    card_bg = "rgba(255, 255, 255, 0.02)" if is_dark else "rgba(255, 255, 255, 1)"
    card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
    row_hover = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.02)"
    
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;800&display=swap');
        
        /* App Background */
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
            font-family: 'Inter', sans-serif;
        }}
        
        h1, h2, h3, p, span {{ color: {text_color} !important; }}
        .subtext {{ color: {sub_text} !important; }}

        /* Artefact Gradient Text */
        .atf-gradient {{
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* Status Cards */
        div[data-testid="stMetric"] {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 8px;
            padding: 1.5rem !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}

        /* Custom Table Rows */
        .lead-row {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 0.5rem;
            transition: all 0.2s ease;
        }}
        .lead-row:hover {{
            background: {row_hover};
            transform: translateY(-1px);
        }}
        
        /* Tier 1 Gradient Bar Indicator (Baseado no seu print da seta) */
        .tier-1-bar {{
            height: 4px;
            width: 100%;
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
            border-radius: 4px 4px 0 0;
            margin-bottom: -4px;
        }}

        /* Color Pills - Artefact Palette */
        .pill-blue {{ color: #3232ff; font-weight: 600; }}
        .pill-magenta {{ color: #ff1493; font-weight: 600; }}
        .pill-neutral {{ color: {sub_text}; font-weight: 500; }}

        /* Custom Dividers */
        hr {{ border-color: {card_border} !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_theme()

# --- 4. DADOS E LÓGICA REFINADA ---
LEADS_BASE = [
    {"id": 1, "nome": "Thais Cristina de Abreu", "empresa": "G5 Partners", "cargo": "VP - People & Culture", "score": 55},
    {"id": 2, "nome": "Mari Stela Ribeiro", "empresa": "HILTI do Brasil", "cargo": "CHRO", "score": 52},
    {"id": 3, "nome": "Brenda Donato Endo", "empresa": "Embracon", "cargo": "Diretora de RH", "score": 45},
    {"id": 4, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "score": 30},
]

def classificar_tier(score):
    if score >= 48: return "Tier 1 - Strategic"
    elif score >= 39: return "Tier 2 - High Priority"
    else: return "Tier 3 - Nurturing"

def estimar_orcamento(tier):
    if "Tier 1" in tier: return "> R$ 1 Milhão"
    elif "Tier 2" in tier: return "R$ 500k - R$ 1M"
    else: return "< R$ 500k"

# Enriquecendo a base
for lead in LEADS_BASE:
    lead['tier'] = classificar_tier(lead.get('score', 0))
    lead['orcamento'] = estimar_orcamento(lead['tier'])

df_leads = pd.DataFrame(LEADS_BASE)

# --- 5. MENU LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient" style="font-size:2rem; margin-bottom:0;">Artefact</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtext" style="margin-bottom:2rem;">Intelligence CRM</p>', unsafe_allow_html=True)
    
    # Lógica de desabilitar botão ativo (Feedback 1)
    is_dash = st.session_state.view_mode == 'dashboard'
    is_pipe = st.session_state.view_mode == 'list'
    
    if st.button("📊 Dashboard Executivo", use_container_width=True, disabled=is_dash):
        st.session_state.view_mode = 'dashboard'
        st.rerun()
        
    if st.button("👥 Pipeline de Leads", use_container_width=True, disabled=is_pipe):
        st.session_state.view_mode = 'list'
        st.rerun()
        
    st.divider()
    
    # Theme Switcher (Feedback 2)
    tema_atual = "🌙 Modo Escuro" if st.session_state.theme == 'dark' else "☀️ Modo Claro"
    if st.button(f"Alternar Tema ({tema_atual})", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()

# --- 6. RENDERIZAÇÃO DA TELA PRINCIPAL ---

if st.session_state.view_mode == 'dashboard':
    st.markdown('<h1 style="margin-bottom:0;">Overview Estratégico</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtext">Visão macro de contas e pipeline.</p>', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Contas Estratégicas (T1)", len(df_leads[df_leads['tier'].str.contains('Tier 1')]))
    c2.metric("Pipeline Ativo", len(df_leads))
    c3.metric("Avg Score", f"{df_leads['score'].mean():.0f} pts")
    
    st.divider()
    
    # Gráfico adaptável ao tema
    font_color = "#ffffff" if st.session_state.theme == 'dark' else "#111111"
    
    tier_counts = df_leads['tier'].value_counts().reset_index()
    tier_counts.columns = ['Tier', 'Volume']
    # Cores Artefact aplicadas no gráfico
    fig = px.bar(tier_counts, x='Volume', y='Tier', orientation='h', color='Tier',
                 color_discrete_sequence=['#3232ff', '#ff1493', '#888890'])
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=font_color,
        showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.view_mode == 'list':
    st.markdown('<h1 style="margin-bottom:0;">Lideranças Mapeadas</h1>', unsafe_allow_html=True)
    st.write("")
    
    # Header da Tabela Customizado
    h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
    h1.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">EXECUTIVO</span>', unsafe_allow_html=True)
    h2.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">EMPRESA</span>', unsafe_allow_html=True)
    h3.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">CLASSIFICAÇÃO</span>', unsafe_allow_html=True)
    h4.markdown('<span class="subtext" style="font-size:0.8rem; font-weight:600;">ORÇAMENTO</span>', unsafe_allow_html=True)
    st.divider()
    
    # Linhas de Leads com CSS Injetado
    for l in LEADS_BASE:
        
        # Lógica de Cores da Artefact baseada no Tier
        if "Tier 1" in l['tier']:
            tier_class = "pill-blue"
            budget_class = "pill-blue"
            grad_bar = '<div class="tier-1-bar"></div>'
        elif "Tier 2" in l['tier']:
            tier_class = "pill-magenta"
            budget_class = "pill-magenta"
            grad_bar = ''
        else:
            tier_class = "pill-neutral"
            budget_class = "pill-neutral"
            grad_bar = ''

        # Container visual personalizado
        st.markdown(f"""
        <div class="lead-row">
            {grad_bar}
            <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 5px;">
                <div style="flex: 3;">
                    <strong style="font-size: 1.1rem;">{l['nome']}</strong><br>
                    <span class="subtext" style="font-size: 0.9rem;">{l['cargo']}</span>
                </div>
                <div style="flex: 2;">{l['empresa']}</div>
                <div style="flex: 2;"><span class="{tier_class}">{l['tier']}</span></div>
                <div style="flex: 2;"><span class="{budget_class}">{l['orcamento']}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão funcional alinhado à direita
        _, btn_col = st.columns([9, 1])
        with btn_col:
            if st.button("Abrir", key=f"btn_{l['id']}", use_container_width=True):
                st.session_state.selected_lead_id = l['id']
                st.session_state.view_mode = 'detail'
                st.rerun()
