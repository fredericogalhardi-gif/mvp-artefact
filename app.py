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


# =====================================================================
# A PARTIR DAQUI, O CÓDIGO SÓ RODA SE O USUÁRIO ESTIVER LOGADO
# =====================================================================

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
    "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",
]
COMPRESSED_LEADS_DATA = "".join(COMPRESSED_CHUNKS)

def sync_initial_leads_to_db():
    try:
        # Pega a string inteira
        b64_str = COMPRESSED_LEADS_DATA
        
        # 1. Limpa possíveis espaços ou quebras de linha invisíveis (causadores do erro)
        b64_str = b64_str.replace('\n', '').replace('\r', '').replace(' ', '')
        
        # 2. Se o tamanho der resto 1 na divisão por 4, significa que um caractere inválido vazou no final
        padding_needed = len(b64_str) % 4
        if padding_needed == 1:
            b64_str = b64_str[:-1] # Remove a sujeira final
            
        # 3. Adiciona o "=" que estiver faltando (Padding correto)
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        
        # Tenta descompactar ANTES de apagar o banco
        leads_json = zlib.decompress(base64.b64decode(b64_str)).decode('utf-8')
        full_leads = json.loads(leads_json)
        
        # DEU CERTO? Agora sim, limpa o banco de dados
        supabase.table("leads").delete().gt("id", 0).execute()
        
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
    
    if st.session_state.current_user == "Fred":
        st.markdown("⚙️ **Painel Admin**")
        st.caption("Forçar o envio de todos os leads originais para o Supabase.")
        if st.button("🔄 Sincronizar Banco", type="primary", use_container_width=True):
            with st.spinner("Descompactando e enviando base em lote..."):
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
            
        if st.session_state.current_user == "Fred":
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
                confirmacao = st.checkbox("Sim, tenho certeza", key=f"chk_del_{n['id']}")
                if confirmacao:
                    if st.button("Apagar Definitivamente", key=f"btn_del_{n['id']}", type="primary"):
                        if delete_note_from_supabase(n['id'], n.get('audio_url'), table="feedback_notas"): 
                            st.rerun()
