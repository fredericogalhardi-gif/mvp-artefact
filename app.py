import streamlit as st
import pandas as pd
import os
import base64
import re
import json
from datetime import datetime
from supabase import create_client, Client
import google.generativeai as genai

# --- 1. CONFIGURAÇÃO C-LEVEL ---
st.set_page_config(
    page_title="Artefact | Contacts",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CONEXÕES (SUPABASE E GEMINI) ---
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

# Inicializa Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    has_gemini = True
except KeyError:
    has_gemini = False
    st.warning("⚠️ GEMINI_API_KEY não encontrada nos secrets. A IA não vai funcionar.")

def flash(message: str, kind: str = "error"):
    st.session_state.setdefault("pending_flashes", []).append((kind, message))

def render_flashes():
    for kind, message in st.session_state.pop("pending_flashes", []):
        getattr(st, kind)(message)

# --- BANCO DE DADOS: NOTAS E INSIGHTS ---
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

def delete_note_from_supabase(note_id: str):
    try:
        supabase.table("notas").delete().eq("id", note_id).execute()
        return True
    except Exception as e:
        return False

def load_insights_from_supabase(lead_id: str):
    try:
        return supabase.table("insights").select("*").eq("lead_id", str(lead_id)).order("created_at", desc=True).execute().data
    except Exception as e: 
        return []

def save_insight_to_supabase(lead_id: str, tipo: str, texto: str):
    try:
        data = {"lead_id": str(lead_id), "tipo": tipo, "texto": texto, "created_at": datetime.now().isoformat()}
        supabase.table("insights").insert(data).execute()
    except Exception as e:
        flash(f"Erro ao salvar insight: {e}")

def upload_audio_to_supabase(audio_bytes, lead_id: str):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_lead_id = re.sub(r'[^a-zA-Z0-9]', '', str(lead_id))
        filename = f"registro_{safe_lead_id}_{timestamp}.wav"
        supabase.storage.from_("gravacoes").upload(file=audio_bytes, path=filename, file_options={"content-type": "audio/wav"})
        return supabase.storage.from_("gravacoes").get_public_url(filename)
    except Exception as e: 
        return None

# --- A MÁGICA DA IA (GEMINI BLINDADO) AQUI ---
def processar_audio_com_ia(audio_bytes_bruto):
    if not has_gemini: 
        return "Erro: Gemini não configurado nos secrets.", []
    
    # Lista de modelos do melhor para o "mais garantido"
    modelos_para_testar = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-pro-latest',
        'gemini-1.0-pro'
    ]
    
    prompt = """
    Você é um analista comercial de elite.
    1. Ouça e transcreva o áudio fornecido.
    2. Extraia os insights qualitativos mais valiosos da reunião.
    
    Retorne APENAS um JSON estrito no seguinte formato:
    {
        "transcricao": "texto completo da transcrição aqui",
        "insights": [
            {"tipo": "Nome do Tópico (Ex: Foco, Dor, Oportunidade)", "texto": "Resumo executivo do insight"}
        ]
    }
    """
    
    audio_part = {
        "mime_type": "audio/wav",
        "data": audio_bytes_bruto
    }
    
    ultimo_erro = ""
    
    # O código vai tentar um por um até o Google aceitar
    for nome_modelo in modelos_para_testar:
        try:
            model = genai.GenerativeModel(nome_modelo)
            response = model.generate_content(
                [prompt, audio_part],
                generation_config={"response_mime_type": "application/json"}
            )
            
            dados_json = json.loads(response.text)
            transcricao = dados_json.get("transcricao", "Transcrição não retornada.")
            insights = dados_json.get("insights", [])
            
            # Se deu certo, retorna os dados e para o loop
            return transcricao, insights
            
        except Exception as e:
            ultimo_erro = str(e)
            continue # Ignora o erro e tenta o próximo modelo da lista
            
    # Se TODOS falharem, ele avisa
    return f"Falha na IA. O Google bloqueou todos os modelos tentados. Último erro: {ultimo_erro}", []

# --- 3. GESTÃO DE ESTADO ---
if 'view_mode' not in st.session_state: st.session_state.view_mode = 'list'
if 'selected_lead_id' not in st.session_state: st.session_state.selected_lead_id = None
if 'theme' not in st.session_state: st.session_state.theme = 'dark'
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

# --- 4. LÓGICA DE FOTOS ---
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

# --- 5. DESIGN SYSTEM ---
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
        .stTextArea textarea, .stTextInput input {{ background-color: {C['INPUT_BKG']} !important; color: {C['INPUT_TEXT']} !important; border: 1px solid {C['BORDER']} !important; border-radius: 8px !important; }}
        button[kind="secondary"] {{ background-color: transparent !important; color: {C['TEXT']} !important; border: 1px solid {btn_border} !important; border-radius: 8px !important; width: 100% !important; }}
        button[kind="primary"] {{ background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%) !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; width: 100% !important; font-weight: 600 !important; }}
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
    {"ID": 7, "Nome": "Camila Alves Massaro", "Empresa": "ArcelorMittal Gonvarri", "Cargo": "Director of People, Strategy & IT", "LinkedIn": "https://www.linkedin.com/in/camilamassaro-rh"},
    {"ID": 5, "Nome": "Brenda Donato Endo", "Empresa": "Embracon", "Cargo": "Diretora de RH", "LinkedIn": "https://www.linkedin.com/in/brenda-donato-endo-78275041"},
    {"ID": 42, "Nome": "Willian Souza", "Empresa": "EMS", "Cargo": "Diretor de Governança e Treinamento", "LinkedIn": "https://www.linkedin.com/in/willian-souza-63874147"},
    {"ID": 15, "Nome": "Danila Pires Carsoso", "Empresa": "Motiva", "Cargo": "Diretor", "LinkedIn": ""},
    {"ID": 21, "Nome": "Frederico Consetino Neto", "Empresa": "Afya", "Cargo": "Diretor de Recursos Humanos", "LinkedIn": "https://www.linkedin.com/in/freico-cosentino-b67b1a20"},
    {"ID": 33, "Nome": "Patrícia Rosado", "Empresa": "Tupy", "Cargo": "VP de Pessoas, Cultura e SSMA", "LinkedIn": "https://www.linkedin.com/in/patricia-rosado-b15ba01a"},
    {"ID": 20, "Nome": "Franciele Ropelato", "Empresa": "Merck", "Cargo": "Diretora De RH", "LinkedIn": ""},
    {"ID": 35, "Nome": "RITA SOUZA", "Empresa": "Bunge Alimentos", "Cargo": "Diretora Gestão Mudança Organizacional", "LinkedIn": "https://www.linkedin.com/in/rita-souza-neurochange/"},
    {"ID": 38, "Nome": "Soraya Bahde", "Empresa": "Bradesco", "Cargo": "Diretora", "LinkedIn": "https://www.linkedin.com/in/sorayabahde"},
    {"ID": 32, "Nome": "Patricia Bobbato", "Empresa": "Natura", "Cargo": "Diretora de Cultura, Desenvolvimento, Bem estar e DE&I", "LinkedIn": "https://www.linkedin.com/in/patriciabobbato"},
    {"ID": 13, "Nome": "Daniela Monteiro", "Empresa": "Editora do Brasil", "Cargo": "Diretora de RH & Marca", "LinkedIn": "https://br.linkedin.com/in/daniela-monteiro-a3125970"},
    {"ID": 16, "Nome": "Diná Ribeiro de Carvalho", "Empresa": "Superlógica", "Cargo": "Diretora de Gente e Gestão", "LinkedIn": "https://br.linkedin.com/in/din%C3%A1-ribeiro-de-carvalho-a1a184348"},
    {"ID": 31, "Nome": "Neto Mello", "Empresa": "Adimax", "Cargo": "Diretor de RH / CHRO", "LinkedIn": "https://www.linkedin.com/in/netomello"},
    {"ID": 22, "Nome": "Gerson Cosme santos", "Empresa": "GHT", "Cargo": "Diretor gente & performance", "LinkedIn": "https://www.linkedin.com/in/gerson-cosme-santos"},
    {"ID": 2, "Nome": "Ana Luiza Guimarães Brasil", "Empresa": "Fortbras", "Cargo": "Diretor de Gente e Gestão", "LinkedIn": "https://www.linkedin.com/in/brasilana"},
    {"ID": 36, "Nome": "Rosangela Schneider", "Empresa": "Karsten SA", "Cargo": "CHRO", "LinkedIn": ""},
    {"ID": 40, "Nome": "Thais Cristina de Abreu Vendramini Ferreira", "Empresa": "G5 Partners", "Cargo": "Vice President - People and Culture Manager", "LinkedIn": "https://www.linkedin.com/in/thais-vendramini/"},
    {"ID": 4, "Nome": "Angelo Fanti", "Empresa": "Sorocaba Refrescos S/A", "Cargo": "Diretor Recursos Humanos", "LinkedIn": "https://br.linkedin.com/in/angelo-fanti-58a4a821"},
    {"ID": 25, "Nome": "Juliana Dorigo", "Empresa": "Grupo Ecoagro", "Cargo": "Diretora de RH", "LinkedIn": "https://www.linkedin.com/in/julianadorigorh"},
    {"ID": 39, "Nome": "Tâmara Costa", "Empresa": "SantoDigital", "Cargo": "Diretora de RH", "LinkedIn": "https://www.linkedin.com/in/tamiscosta"},
    {"ID": 1, "Nome": "Aldo Silva dos Santos", "Empresa": "HCOSTA", "Cargo": "CHRO Gente e Gestão", "LinkedIn": "https://www.linkedin.com/in/aldo-santos-a4985353/"},
    {"ID": 23, "Nome": "GIOVANI CARRA", "Empresa": "ADF ONDULADOS E LOGISTICA", "Cargo": "DIRETOR DE RH", "LinkedIn": "https://www.linkedin.com/in/giovani-carra-65858a33"},
    {"ID": 10, "Nome": "Caroline Faki de Miranda", "Empresa": "Vigor Alimentos", "Cargo": "Head de Business Partner", "LinkedIn": "https://www.linkedin.com/in/caroline-faki-68338285"},
    {"ID": 17, "Nome": "Diogo Dourado Soares", "Empresa": "Festo Brasil", "Cargo": "Head of HR CoE SAM", "LinkedIn": ""},
    {"ID": 27, "Nome": "Leonardo Rodrigues Gaspar", "Empresa": "SIMPRESS", "Cargo": "Gerente Executivo RH", "LinkedIn": ""},
    {"ID": 24, "Nome": "Jader Eder Bleil", "Empresa": "Greenbrier Maxion", "Cargo": "Gerente RT", "LinkedIn": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225"},
    {"ID": 14, "Nome": "Daniela Nishimoto", "Empresa": "Grupo L'Oréal", "Cargo": "CHRO", "LinkedIn": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1"},
    {"ID": 43, "Nome": "Daniele Intrebartoli Costa", "Empresa": "Heineken", "Cargo": "Gerente Sr People", "LinkedIn": ""},
    {"ID": 41, "Nome": "Thamires Justino", "Empresa": "Alcoa Alumínio", "Cargo": "Gerente de RH", "LinkedIn": "https://www.linkedin.com/in/thamires-pedro-15287611b/"},
    {"ID": 11, "Nome": "Daniel Peruchi", "Empresa": "Alcoa", "Cargo": "Gerente Sênior RH", "LinkedIn": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9"},
    {"ID": 37, "Nome": "Sabrina Lemes", "Empresa": "GBMX", "Cargo": "Gerente EHS", "LinkedIn": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107"},
    {"ID": 34, "Nome": "Ricardo Malvestite", "Empresa": "GBMX", "Cargo": "Gerente Sr RH", "LinkedIn": "https://www.linkedin.com/in/ricardo-malvestite-74b1936"},
    {"ID": 26, "Nome": "Lenita David Gilioli", "Empresa": "Flora Produtos", "Cargo": "Gerente executiva RH", "LinkedIn": "https://www.linkedin.com/in/lenita-gilioli-freitas"},
    {"ID": 28, "Nome": "Mariana Macedo Gaida", "Empresa": "Uncover", "Cargo": "Head of People", "LinkedIn": ""},
    {"ID": 29, "Nome": "Michele Ferreira", "Empresa": "Confiança Supermercados", "Cargo": "Coordenadora de DHO", "LinkedIn": "https://www.linkedin.com/in/michele-ferreira-16401083"},
    {"ID": 44, "Nome": "Marianna Biagi Pache", "Empresa": "Emal", "Cargo": "Gerente de Gestão de Pessoas", "LinkedIn": ""},
    {"ID": 3, "Nome": "ANDRE LUIZ EXPEDITO ARANHA", "Empresa": "SUPERLOGICA", "Cargo": "GERENTE DE REMUNERAÇÃO", "LinkedIn": "https://www.linkedin.com/in/andrelearanha"},
    {"ID": 30, "Nome": "Nelson Simeoni Junior", "Empresa": "Superlógica", "Cargo": "Gerente de DHO", "LinkedIn": "https://www.linkedin.com/in/nelsonsimeoni"},
    {"ID": 12, "Nome": "Daniela Matos Faria", "Empresa": "Zamp", "Cargo": "Dir de Talentos e Cultura", "LinkedIn": "https://www.linkedin.com/in/daniela-matos-faria"},
    {"ID": 19, "Nome": "FERNANDO SPINELLI", "Empresa": "CNL Rodovias", "Cargo": "Gerente de RH e SSO", "LinkedIn": ""},
    {"ID": 45, "Nome": "Graziella Albuquerque", "Empresa": "Emal", "Cargo": "Supervisora de RH", "LinkedIn": ""},
    {"ID": 6, "Nome": "Bruno Szarf", "Empresa": "Stefanini", "Cargo": "VP Global", "LinkedIn": "https://www.linkedin.com/in/brunoszarf"},
    {"ID": 8, "Nome": "Camilla Padua", "Empresa": "KPMG", "Cargo": "Sócia", "LinkedIn": "httpswww.linkedin.comincamillapadua"}
]

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 class="atf-gradient">Artefact</h2>', unsafe_allow_html=True)
    if st.button("👥 Contatos", use_container_width=True, disabled=(st.session_state.view_mode=='list')): 
        st.session_state.view_mode='list'
        st.rerun()
    st.divider()
    if st.button("🌓 Toggle Theme", use_container_width=True): 
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()

# --- 8. VIEWS ---
if st.session_state.view_mode == 'list':
    st.markdown('<h1>Contatos</h1>', unsafe_allow_html=True)
    search = st.text_input("🔍 Pesquisar por nome ou empresa...", placeholder="Digite aqui...")
    
    f_leads = [l for l in LEADS_BASE if search.lower() in l['Nome'].lower() or search.lower() in l['Empresa'].lower()]
    
    for l in f_leads:
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
    
    if st.button("← Voltar"): 
        st.session_state.view_mode = 'list'
        st.rerun()
        
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div>
            <h1 style="margin:0;">{l['Nome']}</h1>
            <p class="subtext" style="font-size:1.1rem;">{l['Cargo']} @ {l['Empresa']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if l.get('LinkedIn'): 
        st.link_button("🔗 Ver no LinkedIn", l['LinkedIn'])

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
    else:
        st.caption("Aguardando gravação de áudio para gerar novos insights.")

    st.divider()

    # --- REGISTRO RÁPIDO COM GATILHO PARA LLM ---
    st.markdown("### 🎙️ Gravar Interação")
    st.caption("Fale sobre a reunião. O Gemini ouvirá o áudio e extrairá os insights.")
    
    if hasattr(st, 'audio_input'):
        audio = st.audio_input("Grave aqui", label_visibility="collapsed", key=f"audio_widget_{st.session_state.audio_key}")
        
        if audio:
            with st.spinner("🧠 Gemini está analisando o áudio e extraindo insights..."):
                audio_bytes = audio.read()
                
                # 1. Upload do áudio pro Supabase
                url = upload_audio_to_supabase(audio_bytes, l['LinkedIn'])
                
                # 2. Chama a IA pra transcrever e tirar insights de uma vez só!
                texto_transcrito, novos_insights = processar_audio_com_ia(audio_bytes)
                
                # 3. Salva a transcrição como nota
                if url:
                    nota_formatada = f"🎙️ **Transcrição (Gemini IA):**\n\n_{texto_transcrito}_"
                    save_note_to_supabase(lead_ref, nota_formatada, url)
                else:
                    flash("Upload do áudio falhou, mas a transcrição foi gerada.", "warning")
                    save_note_to_supabase(lead_ref, f"🎙️ **Transcrição (Sem áudio):**\n\n_{texto_transcrito}_")
                
                # 4. Salva os insights estruturados na tabela de insights
                if novos_insights:
                    for insight in novos_insights:
                        save_insight_to_supabase(lead_ref, insight.get("tipo", "Geral"), insight.get("texto", ""))
                
                # Incrementa chave pra limpar o áudio da tela e atualiza
                st.session_state.audio_key += 1
                st.rerun()
    else:
        st.warning("Gravação de voz indisponível no seu navegador/versão.")

    with st.expander("📝 Adicionar nota de texto manual"):
        with st.form("text_note_form", clear_on_submit=True):
            txt = st.text_area("Nota", placeholder="Digite uma nota manual...", label_visibility="collapsed")
            if st.form_submit_button("Salvar Texto", type="primary"):
                if txt.strip():
                    save_note_to_supabase(lead_ref, txt, None)
                    st.rerun()
    
    # --- HISTÓRICO BRUTO ---
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
            if st.button("Deletar", key=f"del_{n['id']}", type="secondary"):
                if delete_note_from_supabase(n['id']): st.rerun()
