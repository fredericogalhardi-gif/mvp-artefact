import streamlit as st
import pandas as pd
import os
import base64
import re
import json
import io
import time
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
    
    # Spinelli adicionado como Gestor (Não é um lead)
    usuarios_permitidos = ["Spinelli (Gestor/Admin)", "André", "Rafael", "Manu", "Paolo", "Ponti", "Fred"]
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

# Base extraída limpa e atualizada da planilha Controle de Leads GT.xlsx
INITIAL_LEADS = [
    {"ID": 1, "Nome": "Giuliane Paulista", "Empresa": "Banco do Brasil", "Cargo": "AI & Analytics Executive", "LinkedIn": "https://www.linkedin.com/in/giulianepaulista/", "Prioritario": False, "Tema": "Construindo confiança na Era da IA: Jornada do Banco do Brasil em governança, capacitação e maturidade", "Descricao": "- Estratégias para construir governança de dados e IA em escala: como estruturar um modelo de governança sólido em uma instituição do porte do Banco do Brasil\n\n- Os caminhos para alfabetizar em dados e IA milhares de colaboradores com diferentes níveis de maturidade, transformando resistência em engajamento.\n\n- Quais métricas e marcos práticos ajudam a avaliar se a organização está evoluindo de forma madura, segura e alinhada às exigências regulatórias do setor financeiro.\n\n- Como o Banco do Brasil equilibra o entusiasmo com novos modelos de IA e a necessidade de garantir respostas confiáveis, transparentes e sem alucinações.\n\n- Reflexões sobre como valores fundamentais de gestão — como resiliência, simplicidade e curiosidade — se mantêm atuais em meio a transformações tecnológicas tão aceleradas.", "Status": "whatsapp não enviado"},
    {"ID": 2, "Nome": "Sara Sitta e Fernanda Vargas", "Empresa": "Ford", "Cargo": "AI & Data Science Lead (Sara)", "LinkedIn": "https://www.linkedin.com/in/sarasitta/", "Prioritario": False, "Tema": "Fast Cases — Dados, IA, pessoas e ROI em empresas brasileiras / Workshop \"Do piloto ao P&L\" / Mesas Colaborativas", "Descricao": "- Como identificar rapidamente oportunidades de Dados e IA na indústria que tenham ciclo curto de implementação e forte potencial de retorno financeiro.\n\n- Quais são os principais gargalos ao mover projetos da fase de testes para a operação diária e como garantir que o ROI seja refletido no balanço financeiro.\n\n- Como definir KPIs claros e atribuir valor financeiro a iniciativas de Inteligência Artificial (de modelos tradicionais a GenAI) \n\n- Como construir uma base de dados sólida e pipelines resilientes para garantir que as aplicações de GenAI operem com dados de alta qualidade e em escala.\n\n- Como ecossistemas abertos de discussão e compartilhamento de casos reais entre empresas brasileiras ajudam a acelerar a maturidade do mercado local de IA.", "Status": "whatsapp não enviado"},
    {"ID": 3, "Nome": "Gabriel Vernalha Ribeiro", "Empresa": "Dasa", "Cargo": "Executivo de Dados, Analytics e IA", "LinkedIn": "https://www.linkedin.com/in/gvribeiro/", "Prioritario": False, "Tema": "Liderando o Futuro / Board Reverse Pitch: A IA muda tudo? / Mesas Colaborativas", "Descricao": "\"- Como liderar a agenda de implementação da IA em um ecossistema tão crítico e regulado quanto o de saúde.\n\n- Como conduzir a conversa com conselheiros e acionistas sem cair no exagero do hype, balanceando grandes promessas com retorno claro de investimento, gestão de riscos e segurança do paciente.\n\n- Estratégias práticas para manter a conformidade (LGPD/hipaa), a privacidade de dados médicos e a qualidade analítica sem travar a inovação\n\n- Como aplicar PMO, OKRs e Design Thinking para gerenciar a carteira de projetos de inteligência artificial, priorizando as iniciativas que trazem maior impacto nos resultados e na jornada do cliente/paciente.\n\n- Como engajar e capacitar equipes multidisciplinares e profissionais da saúde — que muitas vezes resistem à automação —, promovendo a adoção confiável de novas ferramentas.\"", "Status": "whatsapp não enviado"},
    {"ID": 4, "Nome": "Gabriel Mochnacs", "Empresa": "Cielo", "Cargo": "Superintendente de Dados e IA", "LinkedIn": "https://www.linkedin.com/in/gabrielmarruda/", "Prioritario": False, "Tema": "O que ninguém conta sobre escalar IA: falhas, dados, governança e as decisões que fazem pilotos virarem negócio", "Descricao": "- Quais são os principais motivos que fazem projetos promissores falharem e o que a dor da tentativa ensina sobre maturidade de dados.\n\n- Quais decisões técnicas, de governança e de arquitetura precisam ser tomadas no \"dia zero\" para garantir que uma prova de conceito consiga suportar o volume de um gigante de pagamentos como a Cielo.\n\n- A importância de construir capacidades sólidas de observabilidade e arquitetura em nuvem para sustentar modelos avançados de IA sem explodir custos operacionais nem degradar a qualidade dos dados.\n\n- Como conduzir a mudança cultural necessária para que as áreas de negócio realmente adotem e confiem na tomada de decisão orientada por IA.\n\n- Como a educação executiva recente em GenAI ajuda a filtrar o hype e a tomar decisões pragmáticas para construir o modelo operacional das empresas líderes do mercado", "Status": "whatsapp não enviado"},
    {"ID": 5, "Nome": "Gustavo Nery", "Empresa": "Anatel", "Cargo": "CIO", "LinkedIn": "https://www.linkedin.com/in/gustavo-nery-silva/", "Prioritario": False, "Tema": "O que ninguém conta sobre escalar IA: falhas, dados, governança e as decisões que fazem pilotos virarem negócio", "Descricao": "\"- Os gargalos invisíveis e burocráticos de infraestrutura, dados e compras públicas que dificultam que soluções de IA saiam do papel e virem serviço público.\n\n- Como lidar com as falhas inerentes aos modelos de IA em um ambiente estatal onde a transparência e a responsabilidade legal são exigências absolutas perante órgãos de controle e a sociedade.\n\n- TransformaGov e a virada para a gestão pública orientada a dados: lições aprendidas em grandes programas de transformação do Estado que ajudam a desenhar processos para que a IA seja uma alavanca de produtividade e não apenas um hype.\n\n- Como estruturar modelos de governança, interoperabilidade e compartilhamento de dados sensíveis entre diferentes áreas e órgãos federais para viabilizar projetos robustos de IA.\n\n- As dores e aprendizados de usar internamente na agência reguladora as mesmas tecnologias de inteligência artificial que essa mesma agência precisa regular para o mercado de telecomunicações.\"", "Status": "whatsapp não enviado"},
    {"ID": 6, "Nome": "Sabrina Nazario", "Empresa": "Schneider electric", "Cargo": "CDO SAM", "LinkedIn": "https://www.linkedin.com/in/sabrina-nazario-7138a822/", "Prioritario": False, "Tema": "Governança e Estratégia de Dados na América do Sul: Desafios e Escala Regional", "Descricao": "- Os desafios de desenhar e implementar uma estratégia de dados coesa para toda LATAM, considerando as particularidades locais e as diretrizes globais de uma empresa gigante como a Schneider Electric.\n\n- Como estruturar uma governança de dados eficiente que garanta qualidade, conformidade e segurança sem criar burocracia excessiva ou travar a agilidade e a inovação das equipes.\n\n- Quais estratégias e iniciativas práticas têm sido mais eficazes para vencer a resistência à mudança, democratizar o acesso à informação e elevar a maturidade analítica dos times operacionais e executivos.\n\n- Como a Schneider Electric está utilizando dados e IA para impulsionar soluções de eficiência energética, sustentabilidade e automação industrial na América do Sul.", "Status": "whatsapp não enviado"}
]

def load_leads_from_supabase():
    try:
        res = supabase.table("leads").select("*").execute()
        if not res.data:
            for l in INITIAL_LEADS:
                supabase.table("leads").insert({
                    "id": l["ID"],
                    "nome": l["Nome"],
                    "empresa": l["Empresa"],
                    "cargo": l["Cargo"],
                    "linkedin": l["LinkedIn"],
                    "prioritario": l.get("Prioritario", False),
                    "tema": l.get("Tema", ""),
                    "descricao": l.get("Descricao", ""),
                    "status": l.get("Status", "whatsapp não enviado")
                }).execute()
            res = supabase.table("leads").select("*").execute()
            
        return [
            {
                "ID": d["id"],
                "Nome": d["nome"],
                "Empresa": d["empresa"],
                "Cargo": d["cargo"],
                "LinkedIn": d["linkedin"],
                "Prioritario": d.get("prioritario", False),
                "Tema": d.get("tema", ""),
                "Descricao": d.get("descricao", ""),
                "Status": d.get("status", "whatsapp não enviado")
            } for d in res.data
        ]
    except Exception as e:
        flash(f"Erro ao carregar contatos do banco. {e}")
        return INITIAL_LEADS

def save_new_lead_to_supabase(lead_data):
    try:
        supabase.table("leads").insert({
            "id": lead_data["ID"],
            "nome": lead_data["Nome"],
            "empresa": lead_data["Empresa"],
            "cargo": lead_data["Cargo"],
            "linkedin": lead_data["LinkedIn"],
            "prioritario": lead_data["Prioritario"],
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

# Lógica de fallback robusta para gerar o ID/Chave do Lead no sistema
def get_lead_ref(l):
    url = l.get('LinkedIn', '')
    if url and str(url).lower() != 'nan' and url != '#':
        extracted = url.rstrip('/').split('/')[-1]
        if extracted: return extracted
        
    # Chave Automática se não houver LinkedIn (Nome + Empresa)
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
    with st.spinner("Sincronizando contatos..."):
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
                novo_linkedin = st.text_input("Link do LinkedIn")
            
            prioritario_check = st.checkbox("⭐ Marcar como Lead Prioritário")
            
            if st.form_submit_button("Cadastrar Contato", type="primary"):
                if novo_nome.strip():
                    new_id = int(time.time())
                    novo_lead = {
                        "ID": new_id,
                        "Nome": novo_nome.strip(),
                        "Empresa": nova_empresa.strip() or "Não informada",
                        "Cargo": novo_cargo.strip() or "Não informado",
                        "LinkedIn": novo_linkedin.strip(),
                        "Prioritario": prioritario_check,
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
        sort_by = st.selectbox("Ordenar por:", ["Prioridade", "Nome", "Empresa", "Cargo", "Status"])
    
    f_leads = [l for l in st.session_state.leads_list if search.lower() in l['Nome'].lower() or search.lower() in l['Empresa'].lower()]
    
    if sort_by == "Prioridade":
        f_leads.sort(key=lambda x: (not x.get("Prioritario", False), x.get("Nome", "")))
    elif sort_by == "Nome":
        f_leads.sort(key=lambda x: x.get("Nome", ""))
    elif sort_by == "Empresa":
        f_leads.sort(key=lambda x: (x.get("Empresa", ""), x.get("Nome", "")))
    elif sort_by == "Cargo":
        f_leads.sort(key=lambda x: (x.get("Cargo", ""), x.get("Nome", "")))
    elif sort_by == "Status":
        f_leads.sort(key=lambda x: (x.get("Status", ""), x.get("Nome", "")))
    
    for l in f_leads:
        star_html = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
        card = f"""
        <div class="lead-row">
            <div style="display:flex; align-items:center; gap:15px;">
                {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}
                <div style="flex:1;">
                    <strong style="font-size: 1.1rem;">{l['Nome']}</strong> {star_html}<br>
                    <span class="subtext">{l['Cargo']} @ {l['Empresa']}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)
        
        # MENU OCULTO: Acordeão de Informações e Status
        with st.expander("🔽 Ver Tema, Descrição e Atualizar Status"):
            st.markdown(f"**Tema da Entrevista:** {l.get('Tema', 'Não definido')}")
            st.markdown(f"**Descrição:**\n{l.get('Descricao', 'Sem descrição')}")
            
            opcoes_status = ["whatsapp não enviado", "mensagem 01 enviada", "lead respondeu", "lead não respondeu"]
            current_status = l.get('Status', 'whatsapp não enviado')
            if current_status not in opcoes_status:
                current_status = "whatsapp não enviado"
                
            novo_status = st.selectbox(
                "Mudar Status:", 
                opcoes_status, 
                index=opcoes_status.index(current_status), 
                key=f"status_{l['ID']}"
            )
            if novo_status != current_status:
                update_lead_status_in_supabase(l['ID'], novo_status)
                l['Status'] = novo_status
                
        if st.button(f"Abrir Perfil de {l['Nome']}", key=f"v_{l['ID']}", use_container_width=True): 
            st.session_state.selected_lead_id = l['ID']
            st.session_state.view_mode = 'detail'
            st.rerun()
            
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

elif st.session_state.view_mode == 'detail':
    l = next(item for item in st.session_state.leads_list if item['ID'] == st.session_state.selected_lead_id)
    lead_ref = get_lead_ref(l) # Chave ID garantida (LinkedIn ou Nome_Empresa)
    
    if st.button("← Voltar"): 
        st.session_state.view_mode = 'list'
        st.rerun()
        
    star_badge = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div>
            <h1 style="margin:0;">{l['Nome']} {star_badge}</h1>
            <p class="subtext" style="font-size:1.1rem;">{l['Cargo']} @ {l['Empresa']}</p>
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
            
            # CONFIRMAÇÃO DE SEGURANÇA PARA EXCLUSÃO (NOVA)
            with st.expander("🗑️ Excluir esta interação"):
                st.warning("⚠️ Atenção: Esta ação é irreversível e apagará o log e o áudio permanentemente do banco de dados.")
                confirmacao = st.checkbox("Sim, tenho certeza que desejo excluir", key=f"chk_del_{n['id']}")
                if confirmacao:
                    if st.button("Apagar Definitivamente", key=f"btn_del_{n['id']}", type="primary"):
                        if delete_note_from_supabase(n['id'], n.get('audio_url')): 
                            st.rerun()
