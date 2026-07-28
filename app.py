import streamlit as st
import pandas as pd
import os
import base64
import re
import json
import io
from datetime import datetime
from supabase import create_client, Client
from openai import OpenAI

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | Contacts",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CONEXÕES (SUPABASE E OPENAI) ---
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

# Inicializa OpenAI
try:
    openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except KeyError:
    openai_client = None
    st.warning("⚠️ OPENAI_API_KEY não encontrada nos secrets. A IA não vai funcionar.")

def flash(message: str, kind: str = "error"):
    st.session_state.setdefault("pending_flashes", []).append((kind, message))

def render_flashes():
    for kind, message in st.session_state.pop("pending_flashes", []):
        getattr(st, kind)(message)

# --- BANCO DE DADOS: NOTAS E INSIGHTS ---
def load_notes_from_supabase(lead_id: str):
    try:
        return supabase.table("notas").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except: return []

def save_note_to_supabase(lead_id: str, texto: str, audio_url: str = None):
    data = {"lead_id": str(lead_id), "texto": texto, "created_at": datetime.now().isoformat()}
    if audio_url: data["audio_url"] = audio_url
    supabase.table("notas").insert(data).execute()

def delete_note_from_supabase(note_id: str):
    supabase.table("notas").delete().eq("id", note_id).execute()

def load_insights_from_supabase(lead_id: str):
    try:
        return supabase.table("insights").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except: return []

def save_insight_to_supabase(lead_id: str, tipo: str, texto: str):
    data = {"lead_id": str(lead_id), "tipo": tipo, "texto": texto, "created_at": datetime.now().isoformat()}
    supabase.table("insights").insert(data).execute()

def upload_audio_to_supabase(audio_bytes, lead_id: str):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_lead_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))
        filename = f"registro_{safe_lead_id}_{timestamp}.wav"
        supabase.storage.from_("gravacoes").upload(file=audio_bytes, path=filename, file_options={"content-type": "audio/wav"})
        return supabase.storage.from_("gravacoes").get_public_url(filename)
    except: return None

# --- A MÁGICA DA IA AQUI ---
def processar_audio_com_ia(audio_bytes_bruto):
    if not openai_client: return "OpenAI não configurada.", []
    
    # 1. Preparar o arquivo para o Whisper
    audio_file = io.BytesIO(audio_bytes_bruto)
    audio_file.name = "audio.wav"
    
    # 2. Transcrição (Whisper)
    transcricao = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    ).text

    # 3. Extração de Insights Estruturados (GPT-4o)
    prompt_sistema = """
    Você é um analista comercial de elite. Leia a transcrição da reunião e extraia os insights mais importantes.
    Retorne APENAS um JSON estrito no seguinte formato:
    {"insights": [{"tipo": "Nome do Tópico (Ex: Foco, Dores, Orçamento)", "texto": "Resumo executivo do insight"}]}
    """
    
    resposta_ia = openai_client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Transcrição da reunião:\n\n{transcricao}"}
        ]
    )
    
    try:
        dados_json = json.loads(resposta_ia.choices[0].message.content)
        insights = dados_json.get("insights", [])
        return transcricao, insights
    except Exception as e:
        return transcricao, []

# --- 3. GESTÃO DE ESTADO ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

# --- LÓGICA FOTOS / FRONTEND (OMITIDO AQUI PRA ENCURTAR, MAS MANTER O QUE VOCÊ JÁ TINHA) ---
SABI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sabi')

def extract_linkedin_id(url):
    if not url or url == "#" or str(url) == 'nan': return None
    return url.rstrip('/').split('/')[-1]

def get_photo_html(name, url, size_class="large"):
    initials = "".join([w[0] for w in str(name).split()[:2]]).upper()
    return f'<div class="initials-placeholder {size_class}">{initials}</div>'

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
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {C['BKG']}; font-family: 'Inter', sans-serif; color: {C['TEXT']}; }}
        [data-testid="stSidebar"] {{ background-color: {C['SIDEBAR']} !important; border-right: 1px solid {C['BORDER']}; }}
        .atf-gradient {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}
        .profile-pic, .initials-placeholder {{ border-radius: 50%; object-fit: cover; border: 2px solid #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .profile-pic.large, .initials-placeholder.large {{ width: 100px; height: 100px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; }}
        .initials-placeholder {{ background: linear-gradient(135deg, #3232ff, #ff1493); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; }}
        .lead-row {{ background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }}
        .ai-insight-card {{ background: rgba(50, 50, 255, 0.05); border-left: 4px solid #3232ff; padding: 1.2rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem; }}
        .ai-insight-title {{ color: #3232ff; font-weight: 600; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px; }}
        .timeline-item {{ border-left: 2px solid {C['BORDER']}; margin-left: 15px; padding-left: 20px; padding-bottom: 20px; position: relative; }}
        .timeline-item::before {{ content: ''; position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: #ff1493; }}
        .timeline-date {{ font-size: 0.8rem; color: {C['SUB']}; margin-bottom: 5px; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()
render_flashes()

# --- 6. DATABASE ---
LEADS_BASE = [
    {"ID": 18, "Nome": "Elizabeth Sousa Rodrigues", "Empresa": "Grupo Mendes", "Cargo": "Diretor Executivo de Gente e Cultura", "LinkedIn": "https://www.linkedin.com/in/elizabeth-sousa-rodrigues-26086518/"},
    {"ID": 9, "Nome": "Carolina Bussadori", "Empresa": "Grupo St Marche", "Cargo": "Head de Gente & Cultura", "LinkedIn": "linkedin.com/in/carolinabussadorirh/"},
]

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("👥 Contatos", use_container_width=True): st.session_state.view_mode='list'; st.rerun()

# --- 8. VIEWS ---
if st.session_state.view_mode == 'list':
    st.markdown('<h1>Contatos</h1>', unsafe_allow_html=True)
    for l in LEADS_BASE:
        card = f"""
        <div class="lead-row">
            <div style="display:flex; align-items:center; gap:15px;">
                {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}
                <div style="flex:1;">
                    <strong style="font-size: 1.1rem;">{l['Nome']}</strong><br>
                    <span class="subtext">{l['Cargo']} @ {l['Empresa']}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)
        if st.button(f"Abrir Perfil", key=f"v_{l['ID']}", use_container_width=True): 
            st.session_state.selected_lead_id = l['ID']
            st.session_state.view_mode = 'detail'
            st.rerun()

elif st.session_state.view_mode == 'detail':
    l = next(item for item in LEADS_BASE if item['ID'] == st.session_state.selected_lead_id)
    lead_ref = extract_linkedin_id(l['LinkedIn']) or str(l['ID'])
    
    if st.button("← Voltar"): st.session_state.view_mode = 'list'; st.rerun()
        
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div><h1 style="margin:0;">{l['Nome']}</h1><p class="subtext" style="font-size:1.1rem;">{l['Cargo']} @ {l['Empresa']}</p></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- PUXA OS INSIGHTS DO BANCO E EXIBE ---
    insights_db = load_insights_from_supabase(lead_ref)
    
    st.markdown("### 🧠 Insights Gerados (IA)")
    if insights_db:
        for insight in insights_db:
            st.markdown(f"""
            <div class="ai-insight-card">
                <div class="ai-insight-title">✨ {insight['tipo']}</div>
                <div>{insight['texto']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Aguardando gravação de áudio para extrair inteligência.")

    st.divider()

    # --- O GATILHO DA IA NA GRAVAÇÃO DE ÁUDIO ---
    st.markdown("### 🎙️ Gravar Interação")
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave aqui", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        
        if audio:
            with st.spinner("🧠 Analisando áudio com IA e extraindo insights... Isso pode levar alguns segundos."):
                audio_bytes = audio.read()
                
                # 1. Faz upload do arquivo
                url = upload_audio_to_supabase(audio_bytes, l['LinkedIn'])
                
                # 2. Roda a IA no áudio
                texto_transcrito, novos_insights = processar_audio_com_ia(audio_bytes)
                
                # 3. Salva transcrição no histórico geral
                nota_texto = f"🎙️ **Transcrição Automática:**\n\n_{texto_transcrito}_"
                save_note_to_supabase(lead_ref, nota_texto, url)
                
                # 4. Salva cada insight individualmente no Supabase
                if novos_insights:
                    for insight in novos_insights:
                        save_insight_to_supabase(lead_ref, insight.get("tipo", "Geral"), insight.get("texto", ""))
                
                st.session_state.audio_key += 1
                st.rerun()

    # --- HISTÓRICO BRUTO ---
    st.markdown("<br>#### Histórico de Interações", unsafe_allow_html=True)
    for n in load_notes_from_supabase(lead_ref):
        dt = datetime.fromisoformat(n['created_at'].replace('Z', '+00:00')).strftime("%d/%m %H:%M")
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-date">{dt}</div>
            <div>{n['texto']}</div>
        </div>
        """, unsafe_allow_html=True)
        if n.get('audio_url'): st.audio(n['audio_url'])
