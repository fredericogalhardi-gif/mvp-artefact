import streamlit as st
import json
from github import Github
from datetime import datetime
import hmac
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact Strategy CRM", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO (IDENTIDADE ARTEFACT) ---
st.markdown("""
    <style>
    /* Título em Gradiente ATF */
    .atf-gradient-text {
        background: linear-gradient(90deg, #3232ff 0%, #ff1493 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0rem;
    }
    
    /* Subtítulo charmoso */
    .atf-subtitle {
        color: #a0a0a5;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Borda sutil nos containers (Cards) */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        background-color: #16161a;
        border: 1px solid #2d2d33;
        border-radius: 12px;
        padding: 15px;
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

# --- 7. TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown('<p class="atf-gradient-text">Artefact Strategy</p>', unsafe_allow_html=True)
    st.markdown('<p class="atf-subtitle">Acesso Restrito ao CRM</p>', unsafe_allow_html=True)
    
    with st.container():
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
            if check_login(user_input, pass_input):
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- 8. APP LOGADO ---
repo = conectar_github()
notas_globais, sha_banco = carregar_notas(repo)

# --- SIDEBAR (FILTROS) ---
with st.sidebar:
    st.markdown('<p class="atf-gradient-text" style="font-size: 1.5rem;">Filtros</p>', unsafe_allow_html=True)
    busca_nome = st.text_input("Buscar por nome")
    todas_empresas = sorted(list(set([x['empresa'] for x in LEADS_BASE])))
    filtro_empresa = st.multiselect("Filtrar por Empresa", todas_empresas)
    todos_tiers = ["Tier 1", "Tier 2", "Tier 3", "Tier 4"]
    filtro_tier = st.multiselect("Filtrar por Tier", todos_tiers)
    
    st.divider()
    if st.session_state.view_mode == 'detail':
        if st.button("📋 Voltar para a Lista", use_container_width=True):
            st.session_state.view_mode = 'list'
            st.rerun()
            
    if st.button("🚪 Sair do Sistema", use_container_width=True):
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
st.markdown('<p class="atf-gradient-text">Artefact Strategy CRM</p>', unsafe_allow_html=True)
st.markdown('<p class="atf-subtitle">Gestão de Lideranças e Decisores</p>', unsafe_allow_html=True)

if not leads_exibicao:
    st.warning("Nenhum lead encontrado com os filtros atuais.")
else:
    # ---------------------------------------------------------
    # MODO 1: VISUALIZAÇÃO EM LISTA
    # ---------------------------------------------------------
    if st.session_state.view_mode == 'list':
        
        # Grid Header
        h1, h2, h3, h4 = st.columns([3, 3, 2, 2])
        h1.markdown("**Nome**")
        h2.markdown("**Empresa**")
        h3.markdown("**Nível**")
        h4.markdown("**Ação**")
        st.divider()
        
        # Linhas da Lista
        for l in leads_exibicao:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 3, 2, 2], vertical_alignment="center")
                c1.write(f"**{l['nome']}**")
                c2.write(l['empresa'])
                
                # Cores diferentes dependendo do Tier para dar um visual legal
                cor_tier = "blue" if l['tier'] == "Tier 1" else "normal"
                c3.write(f"⭐ :{cor_tier}[{l['tier']}]")
                
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

        selecao = st.selectbox("Navegue por outros perfis:", opcoes_formatadas, index=current_index)
        lead = next(l for l in leads_exibicao if f"[{l['tier']}] {l['nome']} ({l['empresa']})" == selecao)
        st.session_state.selected_lead_id = lead['id']
        
        st.divider()
        
        # --- UI DO PERFIL (Highlights com Métricas) ---
        c1, c2 = st.columns([3, 1])
        with c1:
            st.header(f"{lead['nome']}")
            st.caption(f"ID no Sistema: {lead['id']}")
            
            # Usando st.metric para um design de Dashboard super profissional
            m1, m2, m3 = st.columns(3)
            m1.metric(label="🏢 Empresa", value=lead['empresa'])
            m2.metric(label="⭐ Classificação", value=lead['tier'], delta=f"Score: {lead['score']}", delta_color="off")
            m3.metric(label="💰 Orçamento", value=lead['orcamento'])
            
        with c2:
            if lead['linkedin'] != "#":
                st.link_button("🔗 Abrir LinkedIn", lead['linkedin'], use_container_width=True)

        # Ver Mais
        with st.expander("👁️ Informações Complementares"):
            st.markdown(f"**💼 Cargo Executivo:** {lead['cargo']}")
            st.markdown(f"**⚖️ Tomador de Decisão:** {lead['decisor']}")

        # --- SISTEMA DE ABAS ---
        st.divider()
        tab_doc, tab_hist = st.tabs(["✍️ Novo Documentário", "📜 Histórico Completo"])

        with tab_doc:
            nova_entrada = st.text_area("Descreva a interação:", height=150, key=f"txt_detalhe_{lead['id']}")
            if st.button("💾 Salvar no Documentário", use_container_width=True, type="primary"):
                if nova_entrada.strip():
                    registro = {"id_lead": lead['id'], "data": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": nova_entrada}
                    notas_globais.append(registro)
                    with st.spinner("Sincronizando com o GitHub..."):
                        salvar_nota(repo, notas_globais, sha_banco)
                    st.success("Anotação salva com sucesso!")
                    time.sleep(1)
                    st.rerun()

        with tab_hist:
            historico_lead = [n for n in notas_globais if n.get('id_lead') == lead['id']]
            if not historico_lead:
                st.info("Nenhuma interação registrada ainda.")
            else:
                for n in reversed(historico_lead):
                    with st.container():
                        st.caption(f"📅 {n['data']}")
                        st.write(n['texto'])
                        st.divider()
