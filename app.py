import streamlit as st
import pandas as pd
import os
import base64
import re
import json
import io
import time
import zlib
from datetime import datetime, timedelta
from supabase import create_client, Client
import google.generativeai as genai
from pydub import AudioSegment
import extra_streamlit_components as stx

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | CRM & Market Intel",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GERENCIADOR DE COOKIES ---
cookie_manager = stx.CookieManager()
cookie_user = cookie_manager.get(cookie="artefact_user")
cookie_event = cookie_manager.get(cookie="artefact_event")

# --- 2. SISTEMA DE LOGIN (AUTENTICAÇÃO) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'selected_event_filter' not in st.session_state:
    st.session_state.selected_event_filter = cookie_event if cookie_event else "ILOS"

if not st.session_state.logged_in and cookie_user:
    st.session_state.logged_in = True
    st.session_state.current_user = cookie_user
    st.session_state.selected_event_filter = cookie_event if cookie_event else "ILOS"

def render_login_screen():
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 10vh auto;
            padding: 3rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .atf-gradient { 
            background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            font-weight: 800; 
            font-size: 2.5rem;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="atf-gradient">Artefact</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8E93; margin-bottom: 1rem;'>Selecione seu perfil e evento</p>", unsafe_allow_html=True)
    
    usuarios_permitidos = ["Spinelli", "André", "Rafael", "Manu", "Paolo", "Ponti", "Fred", "Giu", "Mau"]
    usuario_selecionado = st.selectbox("Usuário", usuarios_permitidos)
    evento_selecionado = st.selectbox("Evento que vai cobrir", ["ILOS", "AIDL"])
    senha_digitada = st.text_input("Senha", type="password", placeholder="Digite a senha da equipe...")
    
    if st.button("Acessar Plataforma", type="primary", use_container_width=True):
        senha_correta = st.secrets.get("APP_PASSWORD", "appleads123")
        if senha_digitada == senha_correta:
            st.session_state.logged_in = True
            st.session_state.current_user = usuario_selecionado
            st.session_state.selected_event_filter = evento_selecionado
            
            cookie_manager.set("artefact_user", usuario_selecionado, expires_at=datetime.now() + timedelta(days=365))
            cookie_manager.set("artefact_event", evento_selecionado, expires_at=datetime.now() + timedelta(days=365))
            time.sleep(0.5) 
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
            
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    render_login_screen()
    st.stop()

# --- 3. CONEXÕES (SUPABASE E GEMINI) ---
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Erro Crítico: Credenciais do Supabase não encontradas nos secrets.")
        st.stop()

supabase = get_supabase_client()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    has_gemini = True
except KeyError:
    has_gemini = False
    st.warning("⚠️ GEMINI_API_KEY não encontrada nos secrets.")

def flash(message: str, kind: str = "error"):
    st.session_state.setdefault("pending_flashes", []).append((kind, message))

def render_flashes():
    for kind, message in st.session_state.pop("pending_flashes", []):
        getattr(st, kind)(message)

def comprimir_audio_para_mp3(audio_bytes_wav):
    try:
        audio_original = AudioSegment.from_file(io.BytesIO(audio_bytes_wav), format="wav")
        mp3_io = io.BytesIO()
        audio_original.export(mp3_io, format="mp3", bitrate="32k")
        return mp3_io.getvalue()
    except Exception as e:
        flash(f"Aviso: Não foi possível comprimir o áudio ({str(e)}).", "warning")
        return audio_bytes_wav

# --- 4. BANCO DE DADOS: LEADS, NOTAS E INSIGHTS ---

COMPRESSED_CHUNKS = [
    "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"
]
COMPRESSED_LEADS_DATA = "".join(COMPRESSED_CHUNKS)

def sync_initial_leads_to_db():
    try:
        supabase.table("leads").delete().gt("id", 0).execute()
        
        b64_str = COMPRESSED_LEADS_DATA
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        
        leads_json = zlib.decompress(base64.b64decode(b64_str)).decode('utf-8')
        full_leads = json.loads(leads_json)
        
        lote = []
        for l in full_leads:
            lote.append({
                "id": l["ID"],
                "nome": l["Nome"],
                "empresa": l["Empresa"],
                "cargo": l["Cargo"],
                "industria": l.get("Industria", ""),
                "evento": l.get("Evento", "AIDL"),
                "tipo_registro": l.get("TipoRegistro", "Cliente/Lead"),
                "dia_evento": l.get("DiaEvento", "Outro"),
                "linkedin": l["LinkedIn"],
                "prioritario": l.get("Prioritario", False),
                "podcast": l.get("Podcast", False),
                "tema": l.get("Tema", ""),
                "descricao": l.get("Descricao", ""),
                "status": l.get("Status", "whatsapp não enviado")
            })
        
        supabase.table("leads").insert(lote).execute()
        return True
    except Exception as e:
        flash(f"Erro ao forçar sincronização: {e}")
        return False

def load_leads_from_supabase():
    try:
        res = supabase.table("leads").select("*").execute()
        if not res.data:
            sync_initial_leads_to_db()
            res = supabase.table("leads").select("*").execute()
            
        return [
            {
                "ID": d["id"],
                "Nome": d["nome"],
                "Empresa": d["empresa"],
                "Cargo": d["cargo"],
                "Industria": d.get("industria", ""),
                "Evento": d.get("evento", "AIDL"),
                "TipoRegistro": d.get("tipo_registro", "Cliente/Lead"),
                "DiaEvento": d.get("dia_evento", "Outro"),
                "LinkedIn": d["linkedin"],
                "Prioritario": d.get("prioritario", False),
                "Podcast": d.get("podcast", False),
                "Tema": d.get("tema", ""),
                "Descricao": d.get("descricao", ""),
                "Status": d.get("status", "whatsapp não enviado")
            } for d in res.data
        ]
    except Exception as e:
        flash(f"Erro ao carregar contatos do banco. {e}")
        return []

def save_new_lead_to_supabase(lead_data):
    try:
        supabase.table("leads").insert({
            "id": lead_data["ID"],
            "nome": lead_data["Nome"],
            "empresa": lead_data["Empresa"],
            "cargo": lead_data["Cargo"],
            "industria": lead_data.get("Industria", ""),
            "evento": lead_data.get("Evento", "AIDL"),
            "tipo_registro": lead_data.get("TipoRegistro", "Cliente/Lead"),
            "dia_evento": lead_data.get("DiaEvento", "Outro"),
            "linkedin": lead_data["LinkedIn"],
            "prioritario": lead_data["Prioritario"],
            "podcast": lead_data.get("Podcast", False),
            "tema": lead_data.get("Tema", ""),
            "descricao": lead_data.get("Descricao", ""),
            "status": lead_data.get("Status", "whatsapp não enviado")
        }).execute()
        return True
    except Exception as e:
        flash(f"Erro ao salvar contato: {e}")
        return False

def update_lead_full_info_in_supabase(lead_id, update_dict):
    try:
        supabase.table("leads").update(update_dict).eq("id", lead_id).execute()
        return True
    except Exception as e:
        flash(f"Erro ao atualizar perfil: {e}")
        return False

def get_lead_ref(l):
    return str(l['ID'])

def load_notes_from_supabase(lead_id: str, table="notas"):
    try:
        return supabase.table(table).select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except Exception as e: 
        return []

def save_note_to_supabase(lead_id: str, texto: str, audio_url: str = None, table="notas"):
    try:
        data = {"lead_id": str(lead_id), "texto": texto, "created_at": datetime.now().isoformat()}
        if audio_url: data["audio_url"] = audio_url
        supabase.table(table).insert(data).execute()
    except Exception as e:
        flash(f"Erro ao salvar nota: {e}")

def delete_note_from_supabase(note_id: str, audio_url: str = None, table="notas"):
    try:
        supabase.table(table).delete().eq("id", note_id).execute()
        if audio_url:
            filename = audio_url.split("/")[-1]
            supabase.storage.from_("gravacoes").remove([filename])
        return True
    except Exception as e:
        flash(f"Erro ao excluir: {e}")
        return False

def load_insights_from_supabase(lead_id: str, table="insights"):
    try:
        return supabase.table(table).select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except Exception as e: 
        return []

def delete_all_insights_from_supabase(lead_id: str, table="insights"):
    try:
        supabase.table(table).delete().eq("lead_id", str(lead_id)).execute()
        return True
    except Exception:
        return False

def save_insight_to_supabase(lead_id: str, tipo: str, texto: str, table="insights"):
    try:
        data = {"lead_id": str(lead_id), "tipo": tipo, "texto": texto, "created_at": datetime.now().isoformat()}
        supabase.table(table).insert(data).execute()
    except Exception:
        pass

def upload_audio_to_supabase(audio_bytes, lead_id: str):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_lead_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))
        filename = f"registro_{safe_lead_id}_{timestamp}.mp3"
        supabase.storage.from_("gravacoes").upload(file=audio_bytes, path=filename, file_options={"content-type": "audio/mp3"})
        return supabase.storage.from_("gravacoes").get_public_url(filename)
    except Exception: 
        return None

# --- 5. A MÁGICA DA IA (GEMINI EXPLORADOR) ---
def processar_audio_com_ia(audio_bytes_bruto, insights_anteriores_texto, usuario):
    if not has_gemini: 
        return "Erro: Gemini não configurado.", []
    try:
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        return f"Erro Google: {str(e)}", []
        
    if not modelos_disponiveis:
        return "Erro: Sem modelos de IA.", []

    prompt = f"""
    Você é um analista comercial de elite auxiliando o consultor {usuario}.
    1. Ouça e transcreva o NOVO áudio gravado por {usuario}.
    2. Analise a transcrição junto com os INSIGHTS ANTERIORES listados abaixo.
    3. ATUALIZE e CONSOLIDE os insights. Junte informações do mesmo tópico. Se houver informações de consultores diferentes, integre-as de forma coerente. NUNCA descarte informações importantes dos insights antigos, apenas agregue ou atualize.
    
    --- INSIGHTS ANTERIORES DO CLIENTE ---
    {insights_anteriores_texto}
    --------------------------------------
    
    Retorne APENAS um JSON estrito:
    {{
        "transcricao": "texto da nova transcrição",
        "insights": [
            {{"tipo": "Nome do Tópico", "texto": "Resumo executivo consolidado"}}
        ]
    }}
    """
    
    audio_part = {"mime_type": "audio/mp3", "data": audio_bytes_bruto}
    ultimo_erro = ""
    
    for nome_modelo in modelos_disponiveis:
        if 'embedding' in nome_modelo.lower() or 'aqa' in nome_modelo.lower():
            continue
        try:
            model = genai.GenerativeModel(nome_modelo)
            response = model.generate_content([prompt, audio_part], generation_config={"response_mime_type": "application/json"})
            dados_json = json.loads(response.text)
            return dados_json.get("transcricao", "Gerada sem texto."), dados_json.get("insights", [])
        except Exception as e:
            ultimo_erro = str(e)
            continue
            
    return f"Erro em todos os modelos: {ultimo_erro}", []

def processar_texto_com_ia(texto_bruto, insights_anteriores_texto, usuario):
    if not has_gemini: 
        return []
    try:
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception:
        return []
        
    prompt = f"""
    Você é um analista comercial de elite auxiliando o consultor {usuario}.
    1. Analise o NOVO registro de texto escrito por {usuario}: "{texto_bruto}"
    2. Avalie este texto junto com os INSIGHTS ANTERIORES listados abaixo.
    3. ATUALIZE e CONSOLIDE os insights. Junte informações do mesmo tópico. NUNCA descarte informações importantes dos insights antigos, apenas agregue ou atualize.
    
    --- INSIGHTS ANTERIORES DO CLIENTE ---
    {insights_anteriores_texto}
    --------------------------------------
    
    Retorne APENAS um JSON estrito:
    {{
        "insights": [
            {{"tipo": "Nome do Tópico", "texto": "Resumo executivo consolidado"}}
        ]
    }}
    """
    
    for nome_modelo in modelos_disponiveis:
        if 'embedding' in nome_modelo.lower() or 'aqa' in nome_modelo.lower():
            continue
        try:
            model = genai.GenerativeModel(nome_modelo)
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            dados_json = json.loads(response.text)
            return dados_json.get("insights", [])
        except Exception:
            continue
    return []

def processar_feedback_com_ia(audio_bytes_bruto, feedbacks_anteriores_texto, usuario):
    if not has_gemini: 
        return "Erro: Gemini não configurado.", []
    try:
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        return f"Erro Google: {str(e)}", []
        
    if not modelos_disponiveis:
        return "Erro: Sem modelos de IA.", []

    prompt = f"""
    Você é um Product Manager focado em melhorar o nosso aplicativo de CRM.
    O usuário {usuario} gravou um áudio com comentários, sugestões ou relatando problemas.
    1. Transcreva o NOVO áudio gravado por {usuario}.
    2. Analise a transcrição junto com os FEEDBACKS ANTERIORES listados abaixo.
    3. ATUALIZE e CONSOLIDE os insights. Crie ou junte informações em categorias como: "🐛 Bugs/Erros", "✨ Sugestões de Melhoria", "👍 Pontos Positivos" ou "🤔 Dúvidas". Nunca descarte feedbacks antigos úteis.
    
    --- FEEDBACKS ANTERIORES DO APP ---
    {feedbacks_anteriores_texto}
    --------------------------------------
    
    Retorne APENAS um JSON estrito:
    {{
        "transcricao": "texto da nova transcrição",
        "insights": [
            {{"tipo": "Categoria (Ex: 🐛 Bugs, ✨ Sugestões)", "texto": "Resumo do feedback consolidado"}}
        ]
    }}
    """
    
    audio_part = {"mime_type": "audio/mp3", "data": audio_bytes_bruto}
    ultimo_erro = ""
    
    for nome_modelo in modelos_disponiveis:
        if 'embedding' in nome_modelo.lower() or 'aqa' in nome_modelo.lower():
            continue
        try:
            model = genai.GenerativeModel(nome_modelo)
            response = model.generate_content([prompt, audio_part], generation_config={"response_mime_type": "application/json"})
            dados_json = json.loads(response.text)
            return dados_json.get("transcricao", "Gerada sem texto."), dados_json.get("insights", [])
        except Exception as e:
            ultimo_erro = str(e)
            continue
            
    return f"Erro em todos os modelos: {ultimo_erro}", []

def processar_feedback_texto_com_ia(texto_bruto, feedbacks_anteriores_texto, usuario):
    if not has_gemini: 
        return []
    try:
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception:
        return []

    prompt = f"""
    Você é um Product Manager focado em melhorar o nosso aplicativo de CRM.
    O usuário {usuario} escreveu um feedback de texto com comentários, sugestões ou relatando problemas.
    1. Analise o NOVO texto escrito por {usuario}: "{texto_bruto}"
    2. Avalie este texto junto com os FEEDBACKS ANTERIORES listados abaixo.
    3. ATUALIZE e CONSOLIDE os insights. Crie ou junte informações em categorias como: "🐛 Bugs/Erros", "✨ Sugestões de Melhoria", "👍 Pontos Positivos" ou "🤔 Dúvidas". Nunca descarte feedbacks antigos úteis.
    
    --- FEEDBACKS ANTERIORES DO APP ---
    {feedbacks_anteriores_texto}
    --------------------------------------
    
    Retorne APENAS um JSON estrito:
    {{
        "insights": [
            {{"tipo": "Categoria (Ex: 🐛 Bugs, ✨ Sugestões)", "texto": "Resumo do feedback consolidado"}}
        ]
    }}
    """
    
    for nome_modelo in modelos_disponiveis:
        if 'embedding' in nome_modelo.lower() or 'aqa' in nome_modelo.lower():
            continue
        try:
            model = genai.GenerativeModel(nome_modelo)
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            dados_json = json.loads(response.text)
            return dados_json.get("insights", [])
        except Exception:
            continue
            
    return []

# --- 6. GESTÃO DE ESTADO E INICIALIZAÇÃO DB ---
if 'leads_list' not in st.session_state:
    with st.spinner("Sincronizando base de contatos..."):
        st.session_state.leads_list = load_leads_from_supabase()

if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

SABI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sabi')

def extract_linkedin_id(url):
    if not url or url == "#" or str(url) == 'nan': return None
    return url.rstrip('/').split('/')[-1]

def get_photo_html(name, url, size_class="large"):
    lid = extract_linkedin_id(url)
    if lid:
        file_prefix = f"httpswww.linkedin.comin{lid}"
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG']:
            test_path = os.path.join(SABI_DIR, f"{file_prefix}{ext}")
            if os.path.exists(test_path):
                with open(test_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f'<img src="data:image/png;base64,{b64}" class="profile-pic {size_class}">'
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
    btn_border = "#3232ff" if is_dark else "#D1D1D6"
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {C['BKG']}; font-family: 'Inter', sans-serif; color: {C['TEXT']}; }}
        [data-testid="stSidebar"] {{ background-color: {C['SIDEBAR']} !important; border-right: 1px solid {C['BORDER']}; }}
        .atf-gradient {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}
        .stTextArea textarea, .stTextInput input, .stSelectbox select {{ background-color: {C['INPUT_BKG']} !important; color: {C['INPUT_TEXT']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 8px !important; }}
        button[kind="secondary"] {{ background-color: transparent !important; color: {C['TEXT']} !important; border: 1px solid {btn_border} !important; border-radius: 8px !important; width: 100% !important; }}
        button[kind="primary"] {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; width: 100% !important; font-weight: 600 !important; }}
        .profile-pic, .initials-placeholder {{ border-radius: 50%; object-fit: cover; border: 2px solid #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .profile-pic.large, .initials-placeholder.large {{ width: 100px; height: 100px; }}
        .profile-pic.small, .initials-placeholder.small {{ width: 50px; height: 50px; }}
        .initials-placeholder {{ background: linear-gradient(135deg, #3232ff, #ff1493); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; }}
        .lead-row {{ background: {C['CARD']}; border: 1px solid {C['BORDER']}; border-radius: 12px; padding: 1.2rem; margin-bottom: 0.5rem; position: relative; }}
        .ai-insight-card {{ background: rgba(50, 50, 255, 0.05); border-left: 4px solid #3232ff; padding: 1.2rem; border-radius: 0 8px 8px 0; margin-bottom: 1rem; }}
        .ai-insight-title {{ color: #3232ff; font-weight: 600; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px; }}
        .timeline-item {{ border-left: 2px solid {C['BORDER']}; margin-left: 15px; padding-left: 20px; padding-bottom: 20px; position: relative; }}
        .timeline-item::before {{ content: ''; position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: #ff1493; }}
        .timeline-date {{ font-size: 0.8rem; color: {C['SUB']}; margin-bottom: 5px; }}
        .star-tag {{ background: linear-gradient(90deg, #FFD700 0%, #FFA500 100%); color: #000; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; margin-left: 8px; }}
        .podcast-tag {{ background: linear-gradient(90deg, #FF8C00 0%, #FF4500 100%); color: #fff; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; margin-left: 8px; }}
        .intel-tag {{ background: linear-gradient(90deg, #00BFFF 0%, #1E90FF 100%); color: #fff; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; margin-left: 8px; }}
        .evento-tag {{ background: #3232ff; color: #fff; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; margin-left: 8px; }}
        .status-tag {{ font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; border: 1px solid {C['BORDER']}; margin-left: 8px; color: {C['SUB']}; }}
        .info-box {{ background: {C['INPUT_BKG']}; border: 1px solid {C['BORDER']}; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; }}
        </style>
    """, unsafe_allow_html=True)

apply_executive_styles()
render_flashes()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><span style='font-size: 1.2rem;'>👋 Olá, <b>{st.session_state.current_user}</b>!</span></div>", unsafe_allow_html=True)
    
    st.markdown("**Evento Ativo:**")
    event_filter = st.selectbox("Filtro de Evento", ["ILOS", "AIDL"], index=["ILOS", "AIDL"].index(st.session_state.selected_event_filter), label_visibility="collapsed")
    if event_filter != st.session_state.selected_event_filter:
        st.session_state.selected_event_filter = event_filter
        cookie_manager.set("artefact_event", event_filter, expires_at=datetime.now() + timedelta(days=365))
        st.session_state.view_mode = 'list'
        st.rerun()

    st.divider()

    if st.button("👥 Base / CRM", use_container_width=True, disabled=(st.session_state.view_mode=='list')): 
        st.session_state.view_mode='list'
        st.rerun()

    if st.button("📢 Feedback do App", use_container_width=True, disabled=(st.session_state.view_mode=='feedback')): 
        st.session_state.view_mode='feedback'
        st.rerun()
    
    st.divider()
    
    if st.button("🌓 Tema (Claro/Escuro)", use_container_width=True): 
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()
        
    st.divider()
    
    if st.session_state.current_user == "Spinelli":
        st.markdown("⚙️ **Painel Admin**")
        st.caption("Forçar o envio de todos os leads para o Supabase.")
        if st.button("🔄 Sincronizar Banco", type="primary", use_container_width=True):
            with st.spinner("Limpando e enviando base em lote... Isso leva 2 segundos."):
                if sync_initial_leads_to_db():
                    st.session_state.leads_list = load_leads_from_supabase()
                    st.success("Banco 100% atualizado!")
                    time.sleep(1.5)
                    st.rerun()
        st.divider()
    
    if st.button("🚪 Sair (Logout)", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        cookie_manager.delete("artefact_user")
        time.sleep(0.5)
        st.rerun()

# --- 8. VIEWS ---
if st.session_state.view_mode == 'list':
    st.markdown(f'<h1>Base de Contatos (Evento {st.session_state.selected_event_filter})</h1>', unsafe_allow_html=True)
    
    with st.expander("➕ Adicionar Novo Registro"):
        with st.form("add_contact_form", clear_on_submit=True):
            col_e2, col_e3 = st.columns(2)
            with col_e2:
                novo_tipo = st.selectbox("Tipo de Registro", ["Cliente/Lead", "Inteligência de Mercado"])
            with col_e3:
                novo_dia = st.selectbox("Dia do Evento", ["D1", "D2", "Outro"])

            col1, col2 = st.columns(2)
            with col1:
                novo_nome = st.text_input("Nome completo ou Assunto *")
                novo_cargo = st.text_input("Cargo (Opcional)")
            with col2:
                nova_empresa = st.text_input("Empresa (Opcional)")
                nova_industria = st.text_input("Indústria (Opcional)")
            
            novo_linkedin = st.text_input("Link do LinkedIn (Opcional)")
            
            col_check1, col_check2 = st.columns(2)
            with col_check1:
                prioritario_check = st.checkbox("⭐ Marcar como Prioritário")
            with col_check2:
                podcast_check = st.checkbox("🎙️ Convidado Podcast")
            
            if st.form_submit_button("Salvar no Banco", type="primary"):
                if novo_nome.strip():
                    new_id = int(time.time())
                    novo_lead = {
                        "ID": new_id,
                        "Nome": novo_nome.strip(),
                        "Empresa": nova_empresa.strip(),
                        "Cargo": novo_cargo.strip(),
                        "Industria": nova_industria.strip(),
                        "Evento": st.session_state.selected_event_filter,
                        "TipoRegistro": novo_tipo,
                        "DiaEvento": novo_dia,
                        "LinkedIn": novo_linkedin.strip(),
                        "Prioritario": prioritario_check,
                        "Podcast": podcast_check,
                        "Tema": "",
                        "Descricao": "",
                        "Status": "whatsapp não enviado"
                    }
                    if save_new_lead_to_supabase(novo_lead):
                        st.session_state.leads_list.append(novo_lead)
                        st.success(f"Registro '{novo_nome}' salvo com sucesso!")
                        st.rerun()
                else:
                    st.error("Preencha pelo menos o nome/assunto.")

    col_search, col_sort = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Pesquisar...", placeholder="Pesquisar por nome ou empresa...")
    with col_sort:
        sort_by = st.selectbox("Ordenar por:", ["Prioridade", "Podcast", "Inteligência", "Dia (D1/D2)", "Nome", "Empresa", "Status"])
    
    # Filtra por texto e pelo Evento selecionado na Sidebar
    f_leads = []
    for l in st.session_state.leads_list:
        text_match = search.lower() in l['Nome'].lower() or search.lower() in l.get('Empresa', '').lower() or search.lower() in l.get('Industria', '').lower()
        event_match = l.get('Evento', 'AIDL') == st.session_state.selected_event_filter
        if text_match and event_match:
            f_leads.append(l)
    
    if sort_by == "Prioridade":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), not x.get("Podcast", False), x.get("Nome", "")))
    elif sort_by == "Podcast":
        f_leads.sort(key=lambda x: (not x.get("Podcast", False), not x.get("Prioritario", False), x.get("Nome", "")))
    elif sort_by == "Inteligência":
        f_leads.sort(key=lambda x: (x.get("TipoRegistro", "Cliente/Lead") != "Inteligência de Mercado", x.get("Nome", "")))
    elif sort_by == "Dia (D1/D2)":
        f_leads.sort(key=lambda x: (x.get("DiaEvento", "Outro"), x.get("Nome", "")))
    elif sort_by == "Nome":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Nome", "")))
    elif sort_by == "Empresa":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Empresa", ""), x.get("Nome", "")))
    elif sort_by == "Status":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Status", ""), x.get("Nome", "")))
    
    for l in f_leads:
        star_html = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
        podcast_html = '<span class="podcast-tag">🎙️ Podcast</span>' if l.get("Podcast") else ""
        intel_html = '<span class="intel-tag">🧠 Intel. de Mercado</span>' if l.get("TipoRegistro") == "Inteligência de Mercado" else ""
        evento_html = f'<span class="evento-tag">{l.get("Evento", "AIDL")} - {l.get("DiaEvento", "Outro")}</span>'
        status_html = f"<span class='status-tag'>{l.get('Status', 'whatsapp não enviado')}</span>" if l.get("TipoRegistro") != "Inteligência de Mercado" else ""
        
        info_empresa_industria = f"{l.get('Empresa', '')}"
        if l.get('Industria'):
            info_empresa_industria += f" | {l['Industria']}"
        
        subtexto = f"{l.get('Cargo', '')}"
        if info_empresa_industria.strip():
            subtexto += f" @ {info_empresa_industria}" if subtexto else info_empresa_industria
            
        card = f"""
        <div class="lead-row">
            <div style="display:flex; align-items:center; gap:15px;">
                {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}
                <div style="flex:1;">
                    <strong style="font-size: 1.1rem;">{l['Nome']}</strong> {evento_html} {status_html} {star_html} {podcast_html} {intel_html}<br>
                    <span class="subtext">{subtexto}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)
                
        if st.button(f"Abrir Perfil", key=f"v_{l['ID']}", use_container_width=True): 
            st.session_state.selected_lead_id = l['ID']
            st.session_state.view_mode = 'detail'
            st.rerun()
            
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

elif st.session_state.view_mode == 'detail':
    l = next(item for item in st.session_state.leads_list if item['ID'] == st.session_state.selected_lead_id)
    lead_ref = get_lead_ref(l)
    
    if st.button("← Voltar"): 
        st.session_state.view_mode = 'list'
        st.rerun()
        
    star_badge = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
    podcast_badge = '<span class="podcast-tag">🎙️ Podcast</span>' if l.get("Podcast") else ""
    intel_badge = '<span class="intel-tag">🧠 Inteligência de Mercado</span>' if l.get("TipoRegistro") == "Inteligência de Mercado" else ""
    evento_badge = f'<span class="evento-tag">{l.get("Evento", "AIDL")} - {l.get("DiaEvento", "Outro")}</span>'

    info_empresa_industria = f"{l.get('Empresa', '')}"
    if l.get('Industria'):
        info_empresa_industria += f" | {l['Industria']}"
        
    subtexto = f"{l.get('Cargo', '')}"
    if info_empresa_industria.strip():
        subtexto += f" @ {info_empresa_industria}" if subtexto else info_empresa_industria
            
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div>
            <h1 style="margin:0;">{l['Nome']} {evento_badge} {star_badge} {podcast_badge} {intel_badge}</h1>
            <p class="subtext" style="font-size:1.1rem;">{subtexto}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    url_linkedin = l.get('LinkedIn', '')
    if url_linkedin and url_linkedin != "#" and str(url_linkedin).lower() != 'nan': 
        st.link_button("🔗 Ver no LinkedIn", url_linkedin)

    st.divider()
    
    with st.expander("✏️ Editar Perfil e Tags"):
        with st.form("edit_profile_form"):
            e_nome = st.text_input("Nome", value=l['Nome'])
            col_e1, col_e2 = st.columns(2)
            e_cargo = col_e1.text_input("Cargo", value=l['Cargo'])
            e_empresa = col_e2.text_input("Empresa", value=l.get('Empresa', ''))
            
            col_i1, col_i2 = st.columns(2)
            e_industria = col_i1.text_input("Indústria", value=l.get('Industria', ''))
            e_linkedin = col_i2.text_input("LinkedIn", value=l.get('LinkedIn', ''))
            
            col_t1, col_t2, col_t3 = st.columns(3)
            idx_evento = ["ILOS", "AIDL", "Outro"].index(l.get('Evento', 'AIDL') if l.get('Evento', 'AIDL') in ["ILOS", "AIDL", "Outro"] else "Outro")
            e_evento = col_t1.selectbox("Evento", ["ILOS", "AIDL", "Outro"], index=idx_evento)
            
            idx_tipo = 0 if l.get('TipoRegistro', 'Cliente/Lead') == 'Cliente/Lead' else 1
            e_tipo = col_t2.selectbox("Tipo de Registro", ["Cliente/Lead", "Inteligência de Mercado"], index=idx_tipo)
            
            idx_dia = ["D1", "D2", "Outro"].index(l.get('DiaEvento', 'Outro') if l.get('DiaEvento', 'Outro') in ["D1", "D2", "Outro"] else "Outro")
            e_dia = col_t3.selectbox("Dia do Evento", ["D1", "D2", "Outro"], index=idx_dia)
            
            e_tema = st.text_input("Tema / Assunto de Interesse", value=l.get('Tema', ''))
            e_desc = st.text_area("Descrição", value=l.get('Descricao', ''))
            
            opcoes_status = ["whatsapp não enviado", "mensagem 01 enviada", "lead respondeu", "lead não respondeu"]
            idx_status = opcoes_status.index(l.get('Status', 'whatsapp não enviado') if l.get('Status', 'whatsapp não enviado') in opcoes_status else "whatsapp não enviado")
            e_status = st.selectbox("Status Comercial", opcoes_status, index=idx_status)
            
            col_c1, col_c2 = st.columns(2)
            e_prio = col_c1.checkbox("⭐ Prioritário", value=l.get('Prioritario', False))
            e_pod = col_c2.checkbox("🎙️ Podcast", value=l.get('Podcast', False))
            
            if st.form_submit_button("Salvar Alterações", type="primary"):
                update_dict = {
                    "nome": e_nome,
                    "cargo": e_cargo,
                    "empresa": e_empresa,
                    "industria": e_industria,
                    "linkedin": e_linkedin,
                    "evento": e_evento,
                    "tipo_registro": e_tipo,
                    "dia_evento": e_dia,
                    "tema": e_tema,
                    "descricao": e_desc,
                    "status": e_status,
                    "prioritario": e_prio,
                    "podcast": e_pod
                }
                if update_lead_full_info_in_supabase(l['ID'], update_dict):
                    l.update({
                        'Nome': e_nome, 'Cargo': e_cargo, 'Empresa': e_empresa, 'Industria': e_industria,
                        'LinkedIn': e_linkedin, 'Evento': e_evento, 'TipoRegistro': e_tipo, 'DiaEvento': e_dia,
                        'Tema': e_tema, 'Descricao': e_desc, 'Status': e_status, 'Prioritario': e_prio, 'Podcast': e_pod
                    })
                    st.success("Perfil atualizado!")
                    time.sleep(0.5)
                    st.rerun()

    st.divider()

    insights_db = load_insights_from_supabase(lead_ref)
    st.markdown("### 🧠 Insights Gerados (IA)")
    if insights_db:
        for insight in insights_db:
            st.markdown(f"""
            <div class="ai-insight-card">
                <div class="ai-insight-title">✨ {insight['tipo']}</div>
                <div style="color: {'#FFFFFF' if st.session_state.theme == 'dark' else '#1A1A1C'}; opacity: 0.9;">
                    {insight['texto']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        if st.button("🔄 Resetar Insights da IA", type="secondary"):
            if delete_all_insights_from_supabase(lead_ref):
                st.success("Insights apagados! O próximo registro gerará um resumo do zero.")
                st.rerun()
    else:
        st.caption("Aguardando gravação de áudio ou texto para gerar novos insights.")

    st.divider()

    st.markdown("### 🎙️ Gravar Interação (Áudio)")
    st.caption(f"Gravando como **{st.session_state.current_user}**.")
    
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave aqui", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        if audio:
            with st.spinner("🧠 Processando áudio com IA..."):
                audio_bytes_wav = audio.read()
                audio_bytes_mp3 = comprimir_audio_para_mp3(audio_bytes_wav)
                url = upload_audio_to_supabase(audio_bytes_mp3, lead_ref)
                
                insights_anteriores_texto = "\n".join([f"- {i['tipo']}: {i['texto']}" for i in insights_db]) if insights_db else "Nenhum insight anterior."
                texto_transcrito, novos_insights = processar_audio_com_ia(audio_bytes_mp3, insights_anteriores_texto, st.session_state.current_user)
                
                if url:
                    save_note_to_supabase(lead_ref, f"🎙️ **{st.session_state.current_user}** (Áudio):\n\n_{texto_transcrito}_", url)
                else:
                    save_note_to_supabase(lead_ref, f"🎙️ **{st.session_state.current_user}** (Sem áudio):\n\n_{texto_transcrito}_")
                
                if novos_insights:
                    delete_all_insights_from_supabase(lead_ref)
                    for insight in novos_insights:
                        save_insight_to_supabase(lead_ref, insight.get("tipo", "Geral"), insight.get("texto", ""))
                
                st.session_state.audio_key += 1
                st.rerun()

    st.markdown("<br>### ✍️ Registrar Interação (Texto)", unsafe_allow_html=True)
    with st.form("text_note_form", clear_on_submit=True):
        txt = st.text_area("Anotações em Texto", label_visibility="collapsed", placeholder="Digite os detalhes da conversa, objeções, ou insights capturados...")
        if st.form_submit_button("Salvar Texto e Processar na IA", type="primary"):
            if txt.strip():
                with st.spinner("🧠 Processando texto com IA..."):
                    insights_anteriores_texto = "\n".join([f"- {i['tipo']}: {i['texto']}" for i in insights_db]) if insights_db else "Nenhum insight anterior."
                    novos_insights = processar_texto_com_ia(txt.strip(), insights_anteriores_texto, st.session_state.current_user)
                    
                    save_note_to_supabase(lead_ref, f"👤 **{st.session_state.current_user}** (Texto):\n\n_{txt.strip()}_", None)
                    
                    if novos_insights:
                        delete_all_insights_from_supabase(lead_ref)
                        for insight in novos_insights:
                            save_insight_to_supabase(lead_ref, insight.get("tipo", "Geral"), insight.get("texto", ""))
                    st.rerun()
    
    st.markdown("<br>#### Histórico de Registros Brutos", unsafe_allow_html=True)
    notas = load_notes_from_supabase(lead_ref)
    
    if not notas:
        st.caption("Nenhum registro ainda.")
    else:
        for n in notas:
            dt = datetime.fromisoformat(n['created_at'].replace('Z', '+00:00')).strftime("%d/%m %H:%M")
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-date">{dt}</div>
                <div>{n['texto']}</div>
            </div>
            """, unsafe_allow_html=True)
            if n.get('audio_url'): 
                st.audio(n['audio_url'])
            
            with st.expander("🗑️ Excluir este registro"):
                st.warning("⚠️ Atenção: Esta ação apagará o log permanentemente.")
                confirmacao = st.checkbox("Sim, tenho certeza", key=f"chk_del_{n['id']}")
                if confirmacao:
                    if st.button("Apagar Definitivamente", key=f"btn_del_{n['id']}", type="primary"):
                        if delete_note_from_supabase(n['id'], n.get('audio_url')): 
                            st.rerun()

# --- 9. VIEW DE FEEDBACK DO APP ---
elif st.session_state.view_mode == 'feedback':
    st.markdown("""
    <div style="margin: 20px 0;">
        <h1 style="margin:0;">📢 Feedback do Aplicativo</h1>
        <p class="subtext" style="font-size:1.1rem;">Use este espaço para relatar bugs, sugerir melhorias ou avaliar o uso do CRM.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    feedback_ref = "APP_FEEDBACK" 
    
    insights_db = load_insights_from_supabase(feedback_ref, table="feedback_insights")
    
    st.markdown("### 🧠 Insights Consolidados (UX/UI)")
    if insights_db:
        for insight in insights_db:
            st.markdown(f"""
            <div class="ai-insight-card">
                <div class="ai-insight-title">✨ {insight['tipo']}</div>
                <div style="color: {'#FFFFFF' if st.session_state.theme == 'dark' else '#1A1A1C'}; opacity: 0.9;">
                    {insight['texto']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        if st.session_state.current_user == "Spinelli":
            if st.button("🔄 Resetar Board de Feedbacks", type="secondary"):
                if delete_all_insights_from_supabase(feedback_ref, table="feedback_insights"):
                    st.success("Board apagado! O próximo registro gerará novos insights.")
                    st.rerun()
    else:
        st.caption("Aguardando o primeiro feedback para gerar o board de Produto.")

    st.divider()

    st.markdown("### 🎙️ Gravar Feedback (Áudio)")
    st.caption(f"Você está gravando como **{st.session_state.current_user}**.")
    
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave seu feedback aqui", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        
        if audio:
            with st.spinner("🧠 A IA está categorizando seu feedback..."):
                audio_bytes_wav = audio.read()
                audio_bytes_mp3 = comprimir_audio_para_mp3(audio_bytes_wav)
                url = upload_audio_to_supabase(audio_bytes_mp3, feedback_ref)
                
                feedbacks_anteriores_texto = "\n".join([f"- {i['tipo']}: {i['texto']}" for i in insights_db]) if insights_db else "Nenhum feedback anterior."
                texto_transcrito, novos_insights = processar_feedback_com_ia(audio_bytes_mp3, feedbacks_anteriores_texto, st.session_state.current_user)
                
                if url:
                    save_note_to_supabase(feedback_ref, f"🎙️ **{st.session_state.current_user}** (Áudio):\n\n_{texto_transcrito}_", url, table="feedback_notas")
                else:
                    save_note_to_supabase(feedback_ref, f"🎙️ **{st.session_state.current_user}** (Sem áudio):\n\n_{texto_transcrito}_", table="feedback_notas")
                
                if novos_insights:
                    delete_all_insights_from_supabase(feedback_ref, table="feedback_insights")
                    for insight in novos_insights:
                        save_insight_to_supabase(feedback_ref, insight.get("tipo", "Geral"), insight.get("texto", ""), table="feedback_insights")
                
                st.session_state.audio_key += 1
                st.rerun()

    st.markdown("<br>### ✍️ Escrever Feedback (Texto)", unsafe_allow_html=True)
    with st.form("text_feedback_form", clear_on_submit=True):
        txt = st.text_area("Seu feedback em Texto", label_visibility="collapsed", placeholder="O que podemos melhorar?")
        if st.form_submit_button("Salvar Texto e Processar na IA", type="primary"):
            if txt.strip():
                with st.spinner("🧠 Processando texto com IA..."):
                    feedbacks_anteriores_texto = "\n".join([f"- {i['tipo']}: {i['texto']}" for i in insights_db]) if insights_db else "Nenhum feedback anterior."
                    novos_insights = processar_feedback_texto_com_ia(txt.strip(), feedbacks_anteriores_texto, st.session_state.current_user)
                    
                    save_note_to_supabase(feedback_ref, f"👤 **{st.session_state.current_user}** (Texto):\n\n_{txt.strip()}_", None, table="feedback_notas")
                    
                    if novos_insights:
                        delete_all_insights_from_supabase(feedback_ref, table="feedback_insights")
                        for insight in novos_insights:
                            save_insight_to_supabase(feedback_ref, insight.get("tipo", "Geral"), insight.get("texto", ""), table="feedback_insights")
                    st.rerun()
    
    st.markdown("<br>#### Histórico Bruto de Feedbacks", unsafe_allow_html=True)
    notas = load_notes_from_supabase(feedback_ref, table="feedback_notas")
    
    if not notas:
        st.caption("Nenhum feedback registrado ainda.")
    else:
        for n in notas:
            dt = datetime.fromisoformat(n['created_at'].replace('Z', '+00:00')).strftime("%d/%m %H:%M")
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-date">{dt}</div>
                <div>{n['texto']}</div>
            </div>
            """, unsafe_allow_html=True)
            if n.get('audio_url'): 
                st.audio(n['audio_url'])
            
            with st.expander("🗑️ Excluir este registro"):
                st.warning("⚠️ Atenção: Esta ação apagará o log permanentemente.")
                confirmacao = st.checkbox("Sim, tenho certeza", key=f"chk_del_{n['id']}")
                if confirmacao:
                    if st.button("Apagar Definitivamente", key=f"btn_del_{n['id']}", type="primary"):
                        if delete_note_from_supabase(n['id'], n.get('audio_url'), table="feedback_notas"): 
                            st.rerun()
