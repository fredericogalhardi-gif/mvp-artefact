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
    page_title="Artefact | CRM",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GERENCIADOR DE COOKIES ---
cookie_manager = stx.CookieManager()
cookie_user = cookie_manager.get(cookie="artefact_user")

# --- 2. SISTEMA DE LOGIN (AUTENTICAÇÃO) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if not st.session_state.logged_in and cookie_user:
    st.session_state.logged_in = True
    st.session_state.current_user = cookie_user

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
    st.markdown("<p style='color: #8E8E93; margin-bottom: 1rem;'>Selecione quem você é para acessar</p>", unsafe_allow_html=True)
    
    usuarios_permitidos = ["Spinelli", "André", "Rafael", "Manu", "Paolo", "Ponti", "Fred"]
    usuario_selecionado = st.selectbox("Usuário", usuarios_permitidos, label_visibility="collapsed")
    senha_digitada = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Digite a senha da equipe...")
    
    if st.button("Acessar CRM", type="primary", use_container_width=True):
        senha_correta = st.secrets.get("APP_PASSWORD", "appleads123")
        if senha_digitada == senha_correta:
            st.session_state.logged_in = True
            st.session_state.current_user = usuario_selecionado
            # Salva o cookie para durar 1 ANO (365 dias)
            cookie_manager.set("artefact_user", usuario_selecionado, expires_at=datetime.now() + timedelta(days=365))
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

COMPRESSED_LEADS_DATA = "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"

def sync_initial_leads_to_db():
    try:
        supabase.table("leads").delete().gt("id", 0).execute()
        
        leads_json = zlib.decompress(base64.b64decode(COMPRESSED_LEADS_DATA)).decode('utf-8')
        full_leads = json.loads(leads_json)
        
        lote = []
        for l in full_leads:
            lote.append({
                "id": l["ID"],
                "nome": l["Nome"],
                "empresa": l["Empresa"],
                "cargo": l["Cargo"],
                "industria": l.get("Industria", ""),
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

def update_lead_priority_in_supabase(lead_id, prioritario):
    try:
        supabase.table("leads").update({"prioritario": prioritario}).eq("id", lead_id).execute()
    except Exception as e:
        flash(f"Erro ao atualizar prioridade: {e}")

def update_lead_status_in_supabase(lead_id, novo_status):
    try:
        supabase.table("leads").update({"status": novo_status}).eq("id", lead_id).execute()
    except Exception as e:
        flash(f"Erro ao atualizar status: {e}")

def get_lead_ref(l):
    url = l.get('LinkedIn', '')
    if url and str(url).lower() != 'nan' and url != '#':
        extracted = url.rstrip('/').split('/')[-1]
        if extracted: return extracted
        
    nome = l.get('Nome', '')
    empresa = l.get('Empresa', '')
    fallback = re.sub(r'[^a-zA-Z0-9]', '', f"{nome}_{empresa}").lower()
    return fallback if fallback else str(l['ID'])

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
    
    if st.button("👥 Contatos", use_container_width=True, disabled=(st.session_state.view_mode=='list')): 
        st.session_state.view_mode='list'
        st.rerun()

    # --- BOTÃO DE FEEDBACK DO APP ---
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
    st.markdown('<h1>Contatos (AI Data Leaders)</h1>', unsafe_allow_html=True)
    
    with st.expander("➕ Adicionar Novo Contato"):
        with st.form("add_contact_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                novo_nome = st.text_input("Nome completo *")
                novo_cargo = st.text_input("Cargo")
            with col2:
                nova_empresa = st.text_input("Empresa")
                nova_industria = st.text_input("Indústria")
            
            novo_linkedin = st.text_input("Link do LinkedIn")
            
            col_check1, col_check2 = st.columns(2)
            with col_check1:
                prioritario_check = st.checkbox("⭐ Marcar como Lead Prioritário")
            with col_check2:
                podcast_check = st.checkbox("🎙️ Convidado Podcast")
            
            if st.form_submit_button("Cadastrar Contato", type="primary"):
                if novo_nome.strip():
                    new_id = int(time.time())
                    novo_lead = {
                        "ID": new_id,
                        "Nome": novo_nome.strip(),
                        "Empresa": nova_empresa.strip() or "Não informada",
                        "Cargo": novo_cargo.strip() or "Não informado",
                        "Industria": nova_industria.strip() or "Não informada",
                        "LinkedIn": novo_linkedin.strip(),
                        "Prioritario": prioritario_check,
                        "Podcast": podcast_check,
                        "Tema": "",
                        "Descricao": "",
                        "Status": "whatsapp não enviado"
                    }
                    if save_new_lead_to_supabase(novo_lead):
                        st.session_state.leads_list.append(novo_lead)
                        st.success(f"Contato {novo_nome} cadastrado com sucesso!")
                        st.rerun()
                else:
                    st.error("Preencha pelo menos o nome.")

    col_search, col_sort = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Pesquisar...", placeholder="Pesquisar por nome ou empresa...")
    with col_sort:
        sort_by = st.selectbox("Ordenar por:", ["Prioridade", "Podcast", "Nome", "Empresa", "Indústria", "Cargo", "Status"])
    
    f_leads = [l for l in st.session_state.leads_list if search.lower() in l['Nome'].lower() or search.lower() in l['Empresa'].lower() or search.lower() in l.get('Industria', '').lower()]
    
    if sort_by == "Prioridade":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), not x.get("Podcast", False), x.get("Nome", "")))
    elif sort_by == "Podcast":
        f_leads.sort(key=lambda x: (not x.get("Podcast", False), not x.get("Prioritario", False), x.get("Nome", "")))
    elif sort_by == "Nome":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Nome", "")))
    elif sort_by == "Empresa":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Empresa", ""), x.get("Nome", "")))
    elif sort_by == "Indústria":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Industria", ""), x.get("Nome", "")))
    elif sort_by == "Cargo":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Cargo", ""), x.get("Nome", "")))
    elif sort_by == "Status":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Status", ""), x.get("Nome", "")))
    
    for l in f_leads:
        star_html = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
        podcast_html = '<span class="podcast-tag">🎙️ Podcast</span>' if l.get("Podcast") else ""
        status_html = f"<span class='status-tag'>{l.get('Status', 'whatsapp não enviado')}</span>"
        
        info_empresa_industria = f"{l['Empresa']}"
        if l.get('Industria'):
            info_empresa_industria += f" | {l['Industria']}"
            
        card = f"""
        <div class="lead-row">
            <div style="display:flex; align-items:center; gap:15px;">
                {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}
                <div style="flex:1;">
                    <strong style="font-size: 1.1rem;">{l['Nome']}</strong> {status_html} {star_html} {podcast_html}<br>
                    <span class="subtext">{l['Cargo']} @ {info_empresa_industria}</span>
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
    
    info_empresa_industria = f"{l['Empresa']}"
    if l.get('Industria'):
        info_empresa_industria += f" | {l['Industria']}"
            
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div>
            <h1 style="margin:0;">{l['Nome']} {star_badge} {podcast_badge}</h1>
            <p class="subtext" style="font-size:1.1rem;">{l['Cargo']} @ {info_empresa_industria}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        btn_star_label = "❌ Remover Prioridade" if l.get("Prioritario") else "⭐ Marcar Prioritário"
        if st.button(btn_star_label, use_container_width=True):
            novo_status = not l.get("Prioritario", False)
            update_lead_priority_in_supabase(l["ID"], novo_status)
            l["Prioritario"] = novo_status
            st.rerun()
            
    with col_b:
        url_linkedin = l.get('LinkedIn', '')
        if url_linkedin and url_linkedin != "#" and str(url_linkedin).lower() != 'nan': 
            st.link_button("🔗 Ver no LinkedIn", url_linkedin)
        else:
            st.button("Sem LinkedIn cadastrado", disabled=True)

    st.divider()
    
    # --- O MENU OCULTO COM INFORMAÇÕES E STATUS (EXPANDER) ---
    with st.expander("📋 Informações do Lead"):
        st.markdown(f"**Tema da Entrevista:** {l.get('Tema', 'Não definido')}")
        st.markdown("---")
        st.markdown(l.get('Descricao', 'Sem descrição'))
        st.markdown("---")
        
        opcoes_status = ["whatsapp não enviado", "mensagem 01 enviada", "lead respondeu", "lead não respondeu"]
        current_status = l.get('Status', 'whatsapp não enviado')
        if current_status not in opcoes_status:
            current_status = "whatsapp não enviado"
            
        novo_status = st.selectbox(
            "Atualizar Status do Lead:", 
            opcoes_status, 
            index=opcoes_status.index(current_status), 
            key=f"status_detail_{l['ID']}"
        )
        if novo_status != current_status:
            update_lead_status_in_supabase(l['ID'], novo_status)
            l['Status'] = novo_status
            st.success("Status atualizado!")
            time.sleep(0.5)
            st.rerun()

    st.divider()

    # --- SESSÃO DE INSIGHTS DA IA ---
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
                st.success("Insights apagados! O próximo áudio gerará um resumo do zero.")
                st.rerun()
    else:
        st.caption("Aguardando gravação de áudio para gerar novos insights.")

    st.divider()

    st.markdown("### 🎙️ Gravar Interação")
    st.caption(f"Você está gravando como **{st.session_state.current_user}**.")
    
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave aqui", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        
        if audio:
            with st.spinner("🧠 Processando IA..."):
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

    with st.expander("📝 Adicionar nota manual"):
        with st.form("text_note_form", clear_on_submit=True):
            txt = st.text_area("Nota", label_visibility="collapsed")
            if st.form_submit_button("Salvar Texto", type="primary"):
                if txt.strip():
                    save_note_to_supabase(lead_ref, f"👤 **{st.session_state.current_user}**:\n{txt.strip()}", None)
                    st.rerun()
    
    st.markdown("<br>#### Histórico de Interações", unsafe_allow_html=True)
    notas = load_notes_from_supabase(lead_ref)
    
    if not notas:
        st.caption("Nenhuma interação registrada.")
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
            
            # CONFIRMAÇÃO DE SEGURANÇA PARA EXCLUSÃO
            with st.expander("🗑️ Excluir esta interação"):
                st.warning("⚠️ Atenção: Esta ação é irreversível e apagará o log e o áudio permanentemente do banco de dados.")
                confirmacao = st.checkbox("Sim, tenho certeza que desejo excluir", key=f"chk_del_{n['id']}")
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
                    st.success("Board apagado! O próximo áudio gerará novos insights.")
                    st.rerun()
    else:
        st.caption("Aguardando o primeiro feedback para gerar o board de Produto.")

    st.divider()

    st.markdown("### 🎙️ Gravar Feedback")
    st.caption(f"Você está gravando como **{st.session_state.current_user}**.")
    
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave seu feedback", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        
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

    with st.expander("📝 Adicionar feedback em texto"):
        with st.form("text_feedback_form", clear_on_submit=True):
            txt = st.text_area("Seu feedback", label_visibility="collapsed")
            if st.form_submit_button("Salvar Feedback", type="primary"):
                if txt.strip():
                    save_note_to_supabase(feedback_ref, f"👤 **{st.session_state.current_user}**:\n{txt.strip()}", None, table="feedback_notas")
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
                confirmacao = st.checkbox("Sim, tenho certeza que desejo excluir", key=f"chk_del_{n['id']}")
                if confirmacao:
                    if st.button("Apagar Definitivamente", key=f"btn_del_{n['id']}", type="primary"):
                        if delete_note_from_supabase(n['id'], n.get('audio_url'), table="feedback_notas"): 
                            st.rerun()
