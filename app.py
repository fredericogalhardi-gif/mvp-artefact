import streamlit as st
import json
from github import Github
from datetime import datetime
import hmac
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact CRM", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO (IDENTIDADE ARTEFACT REAL) ---
st.markdown("""
    <style>
    /* Fundo principal (Dark Navy baseado no PPTX da Artefact) */
    .stApp {
        background-color: #0B1120;
        color: #F8FAFC;
    }
    
    /* Sidebar mais escura para dar profundidade */
    [data-testid="stSidebar"] {
        background-color: #06080F !important;
        border-right: 1px solid #1E293B;
    }

    /* Linhas divisórias super sutis */
    hr {
        border-color: #1E293B !important;
    }

    /* Estilo dos Cards das Métricas */
    div[data-testid="stMetric"] {
        background-color: #111827;
        border-left: 4px solid #00E5FF; /* Cyan Artefact */
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
    }

    /* Logo no topo e Títulos */
    .atf-logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 10px;
    }
    .atf-title {
        font-weight: 800;
        font-size: 2.2rem;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .atf-subtitle {
        color: #00E5FF; /* Azul Elétrico ATF */
        font-size: 1.1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 25px;
    }

    /* Botões customizados ATF */
    .stButton > button {
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #00E5FF !important;
        color: #0B1120 !important;
        font-weight: bold !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #00B4D8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS COMPLETO (45 LEADS) ---
LEADS_BASE = [
    {"id": 1, "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf", "score": 55, "orcamento": "N/I"},
    {"id": 2, "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP de Pessoas, Cultura e SSMA", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a", "score": 52, "orcamento": "N/I"},
    {"id": 3, "nome": "Aldo Silva dos Santos", "empresa": "HCOSTA", "cargo": "CHRO Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/", "score": 50, "orcamento": "N/I"},
    {"id": 4, "nome": "Thais Cristina de Abreu Vendramini Ferreira", "empresa": "G5 Partners", "cargo": "Vice President - People and Culture Manager", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/thais-vendramini/", "score": 49, "orcamento": "N/I"},
    {"id": 5, "nome": "Mari Stela Ribeiro", "empresa": "HILTI do Brasil", "cargo": "CHRO", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/mariribeiro", "score": 48, "orcamento": "N/I"},
    {"id": 6, "nome": "Brenda Donato Endo", "empresa": "Embracon", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041", "score": 47, "orcamento": "N/I"},
    {"id": 7, "nome": "Soraya Bahde", "empresa": "Bradesco", "cargo": "Diretora", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/sorayabahde", "score": 46, "orcamento": "N/I"},
    {"id": 8, "nome": "Ana Luiza Guimarães Brasil", "empresa": "Fortbras", "cargo": "Diretor de Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brasilana", "score": 45, "orcamento": "N/I"},
    {"id": 9, "nome": "Daniela Matos Faria", "empresa": "Zamp", "cargo": "Diretora de Talentos e Cultura", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-matos-faria", "score": 44, "orcamento": "N/I"},
    {"id": 10, "nome": "Patricia Bobbato", "empresa": "Natura", "cargo": "Diretora de Cultura, Desenvolvimento, Bem estar e DE&I", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/patriciabobbato", "score": 43, "orcamento": "N/I"},
    {"id": 11, "nome": "Juliana Dorigo", "empresa": "Grupo Ecoagro", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/julianadorigorh", "score": 42, "orcamento": "N/I"},
    {"id": 12, "nome": "Daniela Nishimoto", "empresa": "Grupo L'Oréal", "cargo": "Diretora/ Executiva de Relações Humanas", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-nishimoto-00b63b1", "score": 41, "orcamento": "N/I"},
    {"id": 13, "nome": "Danila Pires Carsoso", "empresa": "Motiva", "cargo": "Diretor", "decisor": "N/I", "linkedin": "#", "score": 40, "orcamento": "N/I"},
    {"id": 14, "nome": "RITA SOUZA", "empresa": "Bunge Alimentos", "cargo": "Diretora Gestão Mudança Organizacional", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/rita-souza-neurochange/", "score": 39, "orcamento": "N/I"},
    {"id": 15, "nome": "GIOVANI CARRA", "empresa": "ADF ONDULADOS E LOGISTICA", "cargo": "DIRETOR DE RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/giovani-carra-65858a33", "score": 38, "orcamento": "N/I"},
    {"id": 16, "nome": "Gerson Cosme santos", "empresa": "GHT", "cargo": "Diretor gente & performance", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/gerson-cosme-santos", "score": 37, "orcamento": "N/I"},
    {"id": 17, "nome": "Neto Mello", "empresa": "Adimax", "cargo": "Diretor de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/netomello", "score": 36, "orcamento": "N/I"},
    {"id": 18, "nome": "Camila Alves Massaro", "empresa": "ArcelorMittal Gonvarri", "cargo": "Director of People, Strategy & IT", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/camilamassaro-rh", "score": 35, "orcamento": "N/I"},
    {"id": 19, "nome": "Willian Souza", "empresa": "EMS", "cargo": "Diretor de Governança e Treinamento", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/willian-souza-63874147", "score": 34, "orcamento": "N/I"},
    {"id": 20, "nome": "Angelo Fanti", "empresa": "Sorocaba Refrescos S/A", "cargo": "Diretor Recursos Humanos", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/angelo-fanti-58a4a821", "score": 33, "orcamento": "N/I"},
    {"id": 21, "nome": "Daniela Monteiro", "empresa": "Editora do Brasil", "cargo": "Diretora de RH & Marca", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/daniela-monteiro-a3125970", "score": 32, "orcamento": "N/I"},
    {"id": 22, "nome": "Mario Felicio Neto", "empresa": "CPQD", "cargo": "Diretor de Gente e gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/mario-felicio-neto", "score": 31, "orcamento": "N/I"},
    {"id": 23, "nome": "Frederico Consetino Neto", "empresa": "Afya", "cargo": "Diretor de Recursos Humanos", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/frederico-cosentino-b67b1a20", "score": 30, "orcamento": "N/I"},
    {"id": 24, "nome": "Tâmara Costa", "empresa": "SantoDigital", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/tamiscosta", "score": 29, "orcamento": "N/I"},
    {"id": 25, "nome": "Diná Ribeiro de Carvalho", "empresa": "Superlógica", "cargo": "Diretora de Gente e Gestão", "decisor": "Sim", "linkedin": "https://br.linkedin.com/in/diná-ribeiro-de-carvalho-a1a184348", "score": 28, "orcamento": "N/I"},
    {"id": 26, "nome": "Alisson Gratão", "empresa": "Copagril", "cargo": "Superintendente de Gestão de Pessoas", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/alisson1", "score": 27, "orcamento": "N/I"},
    {"id": 27, "nome": "Lenita David Gilioli Pedreira de Freitas", "empresa": "Flora Produtos", "cargo": "Gerente executiva de RH", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/lenita-gilioli-freitas", "score": 26, "orcamento": "N/I"},
    {"id": 28, "nome": "Daniel Peruchi", "empresa": "Alcoa", "cargo": "Gerente Sênior RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/daniel-peruchi-6a09a0b9", "score": 25, "orcamento": "N/I"},
    {"id": 29, "nome": "Thamires Cristina Alves Pedro Justino", "empresa": "Alcoa Alumínio", "cargo": "Gerente de RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/thamires-pedro-15287611b/", "score": 24, "orcamento": "N/I"},
    {"id": 30, "nome": "Ariana Tertuliano", "empresa": "Casa do Construtor", "cargo": "Gerente de RH", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/ariana-tertuliano-81a65538", "score": 23, "orcamento": "N/I"},
    {"id": 31, "nome": "Ricardo Malvestite", "empresa": "GBMX", "cargo": "Gerente Sr RH", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/ricardo-malvestite-74b1936", "score": 22, "orcamento": "N/I"},
    {"id": 32, "nome": "Sabrina Geraldo Rosa Lemes", "empresa": "GBMX", "cargo": "Gerente EHS", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/sabrina-rosa-lemes-mba-4ba065107", "score": 21, "orcamento": "N/I"},
    {"id": 33, "nome": "Jader Éder Bleil", "empresa": "Greenbrier Maxion", "cargo": "Gerente de Relações Trabalhistas e Sindicais", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225", "score": 20, "orcamento": "N/I"},
    {"id": 34, "nome": "ANDRE LUIZ EXPEDITO ARANHA", "empresa": "SUPERLOGICA", "cargo": "GERENTE DE REMUNERAÇÃO", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/andrelearanha", "score": 19, "orcamento": "N/I"},
    {"id": 35, "nome": "Nelson Simeoni Junior", "empresa": "Superlógica", "cargo": "Gerente de DHO", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/nelsonsimeoni", "score": 18, "orcamento": "N/I"},
    {"id": 36, "nome": "Caroline Faki de Miranda", "empresa": "Vigor Alimentos", "cargo": "Head de Business Partner", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/caroline-faki-68338285", "score": 17, "orcamento": "N/I"},
    {"id": 37, "nome": "Marcelo Carlos Pinheiro", "empresa": "Greenbrier Maxion", "cargo": "Gerente Senior", "decisor": "Parcial", "linkedin": "https://www.linkedin.com/in/marcelo-pinheiro-274abb24", "score": 16, "orcamento": "N/I"},
    {"id": 38, "nome": "Jader Eder Bleil", "empresa": "Greenbrier Maxion Equipamentos", "cargo": "Gerente RT", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/jader-%C3%A9der-bleil-41115225", "score": 15, "orcamento": "N/I"},
    {"id": 39, "nome": "Michele Ferreira", "empresa": "Confiança Supermercados", "cargo": "Coordenadora de DHO", "decisor": "Não", "linkedin": "https://www.linkedin.com/in/michele-ferreira-16401083", "score": 14, "orcamento": "N/I"},
    {"id": 40, "nome": "Frederico Galhardi Borges", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7398823203906928642/", "score": 13, "orcamento": "N/I"}
]

# --- 3. LÓGICA DE TIER ---
def calcular_tier(score):
    if score >= 48: return "Tier 1"
    elif score >= 39: return "Tier 2"
    elif score >= 20: return "Tier 3"
    else: return "Tier 4"

for lead in LEADS_BASE:
    lead['tier'] = calcular_tier(lead.get('score', 0))

# ⚠️ REPOSITÓRIO GITHUB
NOME_DO_REPOSITORIO = "fredericogalhardi-gif/mvp-artefact" 

# --- 4. FUNÇÕES DE SEGURANÇA ---
def check_login(user, pwd):
    val_user = st.secrets.get("APP_USER", "BLOQUEADO")
    val_pass = st.secrets.get("APP_PASS", "BLOQUEADO")
    user_match = hmac.compare_digest(user, val_user)
    pwd_match = hmac.compare_digest(pwd, val_pass)
    if not (user_match and pwd_match):
        time.sleep(1.5)
        return False
    return True

# --- 5. FUNÇÕES DE DADOS (GITHUB) ---
@st.cache_resource
def conectar_github():
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        return g.get_repo(NOME_DO_REPOSITORIO)
    except:
        return None

def carregar_notas(repo):
    try:
        arquivo = repo.get_contents("banco.json")
        return json.loads(arquivo.decoded_content.decode("utf-8")), arquivo.sha
    except:
        return [], None

def salvar_nota(repo, lista_notas, sha):
    conteudo = json.dumps(lista_notas, indent=4)
    if sha:
        repo.update_file("banco.json", "CRM: Nova nota adicionada", conteudo, sha)
    else:
        repo.create_file("banco.json", "CRM: Criando banco de dados", conteudo)

# --- 6. LÓGICA DE SESSÃO E NAVEGAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'list'
if 'selected_lead_id' not in st.session_state:
    st.session_state.selected_lead_id = None

# --- COMPONENTE VISUAL DO CABEÇALHO ---
def renderizar_cabecalho_atf():
    # Usando a logo oficial branca da Artefact via URL
    logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Artefact_logo.svg/1024px-Artefact_logo.svg.png"
    st.markdown(f"""
        <div class="atf-logo-container">
            <img src="{logo_url}" width="160" onerror="this.style.display='none'">
        </div>
        <p class="atf-title">Strategy CRM</p>
        <p class="atf-subtitle">Gestão de Lideranças e Decisores</p>
    """, unsafe_allow_html=True)

# --- 7. TELA DE LOGIN ---
if not st.session_state.logado:
    renderizar_cabecalho_atf()
    
    with st.container():
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema", use_container_width=True, type="primary"):
            if check_login(user_input, pass_input):
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("🔒 Usuário ou senha incorretos.")
    st.stop()

# --- 8. APP LOGADO ---
repo = conectar_github()
notas_globais, sha_banco = carregar_notas(repo)

# --- SIDEBAR (FILTROS) ---
with st.sidebar:
    st.markdown('<p class="atf-subtitle" style="font-size: 1.3rem;">Filtros de Busca</p>', unsafe_allow_html=True)
    busca_nome = st.text_input("Nome do Lead")
    todas_empresas = sorted(list(set([x['empresa'] for x in LEADS_BASE])))
    filtro_empresa = st.multiselect("Empresa", todas_empresas)
    todos_tiers = ["Tier 1", "Tier 2", "Tier 3", "Tier 4"]
    filtro_tier = st.multiselect("Classificação (Tier)", todos_tiers)
    
    st.divider()
    if st.session_state.view_mode == 'detail':
        if st.button("📋 Voltar para a Lista", use_container_width=True):
            st.session_state.view_mode = 'list'
            st.rerun()
            
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

# APLICAÇÃO DOS FILTROS
leads_exibicao = LEADS_BASE
if busca_nome:
    leads_exibicao = [l for l in leads_exibicao if busca_nome.lower() in l['nome'].lower()]
if filtro_empresa:
    leads_exibicao = [l for l in leads_exibicao if l['empresa'] in filtro_empresa]
if filtro_tier:
    leads_exibicao = [l for l in leads_exibicao if l['tier'] in filtro_tier]

# --- RENDERIZAÇÃO DA INTERFACE PRINCIPAL ---
renderizar_cabecalho_atf()

if not leads_exibicao:
    st.warning("Nenhum lead encontrado com os parâmetros atuais.")
else:
    # ---------------------------------------------------------
    # MODO 1: VISUALIZAÇÃO EM LISTA (CORRIGIDA)
    # ---------------------------------------------------------
    if st.session_state.view_mode == 'list':
        
        # Dicionário de cores corretas suportadas pelo Streamlit
        cores_suportadas = {
            "Tier 1": "red",
            "Tier 2": "orange",
            "Tier 3": "blue",
            "Tier 4": "gray"
        }
        
        h1, h2, h3, h4 = st.columns([3, 3, 2, 2])
        h1.markdown("**NOME**")
        h2.markdown("**EMPRESA**")
        h3.markdown("**CLASSIFICAÇÃO**")
        h4.markdown("**AÇÃO**")
        st.divider()
        
        for l in leads_exibicao:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 3, 2, 2], vertical_alignment="center")
                c1.write(f"**{l['nome']}**")
                c2.write(l['empresa'])
                
                # Aplicação da cor corrigida (agora funciona 100%)
                cor_exata = cores_suportadas.get(l['tier'], "gray")
                c3.write(f"⭐ :{cor_exata}[**{l['tier']}**]")
                
                if c4.button("👁️ Detalhar", key=f"btn_{l['id']}", use_container_width=True):
                    st.session_state.selected_lead_id = l['id']
                    st.session_state.view_mode = 'detail'
                    st.rerun()
            st.divider()

    # ---------------------------------------------------------
    # MODO 2: VISUALIZAÇÃO ÚNICA (DETALHES DO LEAD)
    # ---------------------------------------------------------
    elif st.session_state.view_mode == 'detail':
        
        opcoes_formatadas = [f"[{l['tier']}] {l['nome']} ({l['empresa']})" for l in leads_exibicao]
        try:
            current_lead = next(l for l in leads_exibicao if l['id'] == st.session_state.selected_lead_id)
            current_formatted = f"[{current_lead['tier']}] {current_lead['nome']} ({current_lead['empresa']})"
            current_index = opcoes_formatadas.index(current_formatted)
        except:
            current_index = 0

        selecao = st.selectbox("Navegar para outro perfil:", opcoes_formatadas, index=current_index)
        lead = next(l for l in leads_exibicao if f"[{l['tier']}] {l['nome']} ({l['empresa']})" == selecao)
        st.session_state.selected_lead_id = lead['id']
        
        st.divider()
        
        # --- UI DO PERFIL (Highlights com Métricas ATF) ---
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            st.markdown(f"## {lead['nome']}")
            
            m1, m2, m3 = st.columns(3)
            m1.metric(label="Empresa", value=lead['empresa'])
            m2.metric(label="Classificação", value=lead['tier'], delta=f"Score: {lead['score']}", delta_color="off")
            m3.metric(label="Orçamento Estimado", value=lead['orcamento'])
            
        with c2:
            if lead['linkedin'] != "#":
                st.link_button("🔗 Acessar LinkedIn", lead['linkedin'], use_container_width=True)

        # Ver Mais
        with st.expander("👁️ Informações Complementares"):
            st.markdown(f"**Cargo Executivo:** {lead['cargo']}")
            st.markdown(f"**Tomador de Decisão:** {lead['decisor']}")

        # --- SISTEMA DE ABAS ---
        st.divider()
        tab_doc, tab_hist = st.tabs(["✍️ Adicionar Documentário", "📜 Histórico de Interações"])

        with tab_doc:
            nova_entrada = st.text_area("Descreva a interação ou novos dados estratégicos:", height=150, key=f"txt_detalhe_{lead['id']}")
            if st.button("💾 Salvar Registro", use_container_width=True, type="primary"):
                if nova_entrada.strip():
                    registro = {"id_lead": lead['id'], "data": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": nova_entrada}
                    notas_globais.append(registro)
                    with st.spinner("Sincronizando com a base segura..."):
                        salvar_nota(repo, notas_globais, sha_banco)
                    st.success("Anotação salva com sucesso!")
                    time.sleep(1)
                    st.rerun()

        with tab_hist:
            historico_lead = [n for n in notas_globais if n.get('id_lead') == lead['id']]
            if not historico_lead:
                st.info("Nenhuma interação registrada no sistema ainda.")
            else:
                for n in reversed(historico_lead):
                    with st.container():
                        st.caption(f"📅 Registrado em: {n['data']}")
                        st.write(n['texto'])
                        st.divider()
