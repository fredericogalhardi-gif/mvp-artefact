import streamlit as st
import json
from github import Github
from datetime import datetime
import hmac
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact Strategy CRM", layout="wide", initial_sidebar_state="expanded")

# --- 2. BANCO DE DADOS DE LEADS (ADICIONE MAIS AQUI) ---
LEADS_BASE = [
    {"id": "bruno_01", "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf"},
    {"id": "patricia_01", "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP de Pessoas, Cultura e SSMA", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a"},
    {"id": "aldo_01", "nome": "Aldo Silva dos Santos", "empresa": "HCOSTA", "cargo": "CHRO Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/"},
    {"id": "fred_01", "nome": "Frederico Galhardi Borges", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7398823203906928642/"},
    {"id": "brenda_01", "nome": "Brenda Donato Endo", "empresa": "Embracon", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041"}
]

# ⚠️ COLOQUE O SEU REPOSITÓRIO REAL AQUI
NOME_DO_REPOSITORIO = "fredericogalhardi-gif/mvp-artefact" 

# --- 3. FUNÇÕES DE SEGURANÇA (ANTI-HACK) ---
def check_login(user, pwd):
    """Verifica credenciais usando comparação segura e segredos do servidor."""
    # Busca os valores no cofre (Secrets) do Streamlit
    val_user = st.secrets.get("APP_USER", "BLOQUEADO")
    val_pass = st.secrets.get("APP_PASS", "BLOQUEADO")

    # hmac.compare_digest evita ataques de tempo (timing attacks)
    user_match = hmac.compare_digest(user, val_user)
    pwd_match = hmac.compare_digest(pwd, val_pass)

    if not (user_match and pwd_match):
        time.sleep(1.5) # Atraso para impedir robôs de força bruta
        return False
    return True

# --- 4. FUNÇÕES DE DADOS (GITHUB) ---
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

# --- 5. LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- 6. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Artefact CRM - Acesso Restrito")
    with st.container():
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if check_login(user_input, pass_input):
                st.session_state.logado = True
                st.success("Acesso autorizado!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- 7. APP LOGADO (INTERFACE E UX) ---
repo = conectar_github()
notas_globais, sha_banco = carregar_notas(repo)

# BARRA LATERAL (FILTROS)
with st.sidebar:
    st.title("🎯 Navegação")
    st.markdown("Use os filtros para encontrar leads específicos.")
    
    busca_nome = st.text_input("Buscar por nome")
    
    # Filtro dinâmico de empresas
    todas_empresas = sorted(list(set([x['empresa'] for x in LEADS_BASE])))
    filtro_empresa = st.multiselect("Filtrar por Empresa", todas_empresas)
    
    st.divider()
    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

# APLICAÇÃO DOS FILTROS
leads_exibicao = LEADS_BASE
if busca_nome:
    leads_exibicao = [l for l in leads_exibicao if busca_nome.lower() in l['nome'].lower()]
if filtro_empresa:
    leads_exibicao = [l for l in leads_exibicao if l['empresa'] in filtro_empresa]

# CONTEÚDO PRINCIPAL
st.title("🚀 Artefact Strategy CRM")

if not leads_exibicao:
    st.warning("Nenhum lead encontrado com os filtros atuais.")
else:
    # Seleção de Lead
    opcoes_formatadas = [f"{l['nome']} ({l['empresa']})" for l in leads_exibicao]
    selecao = st.selectbox("Selecione um perfil para detalhar:", opcoes_formatadas)
    
    # Identifica o lead selecionado
    lead = next(l for l in leads_exibicao if f"{l['nome']} ({l['empresa']})" == selecao)
    
    st.divider()

    # Layout de Informações
    c1, c2 = st.columns([2, 1])
    with c1:
        st.header(lead['nome'])
        st.markdown(f"**🏢 Empresa:** {lead['empresa']}")
        st.markdown(f"**💼 Cargo:** {lead['cargo']}")
        st.markdown(f"**⚖️ Decisor:** {lead['decisor']}")
    with c2:
        st.link_button("🔗 Ver Perfil no LinkedIn", lead['linkedin'], use_container_width=True)

    # SISTEMA DE ABAS (UX MELHORADA)
    tab_doc, tab_hist = st.tabs(["✍️ Documentário (Nova Nota)", "📜 Histórico Completo"])

    with tab_doc:
        st.markdown("### Adicionar ao Documentário")
        nova_entrada = st.text_area("Descreva a interação ou observação:", height=200, placeholder="Ex: Ligação feita hoje, demonstrou interesse em X...")
        
        if st.button("💾 Salvar no Documentário", use_container_width=True):
            if nova_entrada.strip():
                with st.spinner("Sincronizando com a base de dados..."):
                    registro = {
                        "id_lead": lead['id'],
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "texto": nova_entrada
                    }
                    notas_globais.append(registro)
                    salvar_nota(repo, notas_globais, sha_banco)
                    st.success("Informação salva com segurança!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Escreva algo antes de salvar.")

    with tab_hist:
        st.markdown("### Histórico de Interações")
        # Filtra notas apenas deste lead específico
        historico_lead = [n for n in notas_globais if n.get('id_lead') == lead['id']]
        
        if not historico_lead:
            st.info("Ainda não há registros no documentário deste lead.")
        else:
            for n in reversed(historico_lead):
                with st.container():
                    st.caption(f"📅 Registrado em: {n['data']}")
                    st.info(n['texto'])
                    st.divider()
