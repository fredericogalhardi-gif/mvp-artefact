import streamlit as st
import pandas as pd
import os
import base64
import re
import json
import io
import time
import zlib
from datetime import datetime
from supabase import create_client, Client
import google.generativeai as genai
from pydub import AudioSegment

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | CRM",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SISTEMA DE LOGIN (AUTENTICAÇÃO) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

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
    st.markdown("<p style='color: #8E8E93; margin-bottom: 1rem;'>Selecione seu perfil e acesse</p>", unsafe_allow_html=True)
    
    usuarios_permitidos = ["Spinelli", "André", "Rafael", "Manu", "Paolo", "Ponti", "Fred"]
    usuario_selecionado = st.selectbox("Usuário", usuarios_permitidos, label_visibility="collapsed")
    senha_digitada = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Digite a senha da equipe...")
    
    if st.button("Entrar", type="primary", use_container_width=True):
        senha_correta = st.secrets.get("APP_PASSWORD", "appleads123")
        if senha_digitada == senha_correta:
            st.session_state.logged_in = True
            st.session_state.current_user = usuario_selecionado
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

COMPRESSED_LEADS_DATA = "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 "
# --- BULK INSERT DO PDF GTM 3 - PRIORIDADES ---

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

def load_notes_from_supabase(lead_id: str):
    try:
        return supabase.table("notas").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except Exception as e: 
        return []

def save_note_to_supabase(lead_id: str, texto: str, audio_url: str = None):
    try:
        data = {"lead_id": str(lead_id), "texto": texto, "created_at": datetime.now().isoformat()}
        if audio_url: data["audio_url"] = audio_url
        supabase.table("notas").insert(data).execute()
    except Exception as e:
        flash(f"Erro ao salvar nota: {e}")

def delete_note_from_supabase(note_id: str, audio_url: str = None):
    try:
        supabase.table("notas").delete().eq("id", note_id).execute()
        if audio_url:
            filename = audio_url.split("/")[-1]
            supabase.storage.from_("gravacoes").remove([filename])
        return True
    except Exception as e:
        flash(f"Erro ao excluir: {e}")
        return False

def load_insights_from_supabase(lead_id: str):
    try:
        return supabase.table("insights").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except Exception as e: 
        return []

def delete_all_insights_from_supabase(lead_id: str):
    try:
        supabase.table("insights").delete().eq("lead_id", str(lead_id)).execute()
        return True
    except Exception:
        return False

def save_insight_to_supabase(lead_id: str, tipo: str, texto: str):
    try:
        data = {"lead_id": str(lead_id), "tipo": tipo, "texto": texto, "created_at": datetime.now().isoformat()}
        supabase.table("insights").insert(data).execute()
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
    
    st.divider()
    
    if st.button("🌓 Tema (Claro/Escuro)", use_container_width=True): 
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()
        
    st.divider()
    
    # === BOTÃO EXCLUSIVO DE ADMIN (SPINELLI) ===
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
