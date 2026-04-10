import streamlit as st
import json
from github import Github
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact Strategy CRM", layout="wide", initial_sidebar_state="expanded")

# --- BANCO DE DADOS FIXO (LEADS) ---
# Integrei os leads que você enviou no começo do projeto
LEADS_BASE = [
    {"id": "bruno_01", "nome": "Bruno Szarf", "empresa": "Stefanini", "cargo": "VP Global", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brunoszarf"},
    {"id": "patricia_01", "nome": "Patrícia Rosado", "empresa": "Tupy", "cargo": "VP de Pessoas, Cultura e SSMA", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/patricia-rosado-b15ba01a"},
    {"id": "aldo_01", "nome": "Aldo Silva dos Santos", "empresa": "HCOSTA", "cargo": "CHRO Gente e Gestão", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/aldo-santos-a4985353/"},
    {"id": "fred_01", "nome": "Frederico Galhardi Borges", "empresa": "Artefact", "cargo": "Lead Estratégico", "decisor": "Não", "linkedin": "https://www.linkedin.com/feed/update/urn:li:activity:7398823203906928642/"},
    {"id": "brenda_01", "nome": "Brenda Donato Endo", "empresa": "Embracon", "cargo": "Diretora de RH", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/brenda-donato-endo-78275041"},
    {"id": "daniela_01", "nome": "Daniela Matos Faria", "empresa": "Zamp", "cargo": "Diretora de Talentos e Cultura", "decisor": "Sim", "linkedin": "https://www.linkedin.com/in/daniela-matos-faria"}
]

# --- CONFIGURAÇÕES GITHUB ---
# MANTENHA SEU REPOSITÓRIO AQUI
NOME_DO_REPOSITORIO = "fredericogalhardi-gif/mvp-artefact" 

# --- FUNÇÕES DE SEGURANÇA E DADOS ---
def check_login(user, pwd):
    return user == "admin" and pwd == "123456" # Altere sua senha aqui

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
        repo.update_file("banco.json", "Update Notas", conteudo, sha)
    else:
        repo.create_file("banco.json", "Create Notas", conteudo)

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Artefact CRM")
    with st.form("login_form"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar Sistema"):
            if check_login(u, p):
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Credenciais inválidas")
    st.stop()

# --- APP LOGADO ---
repo = conectar_github()
notas_globais, sha_banco = carregar_notas(repo)

# --- SIDEBAR (FILTROS E UX) ---
with st.sidebar:
    st.title("🎯 Filtros")
    busca = st.text_input("Buscar por nome")
    
    lista_empresas = sorted(list(set([x['empresa'] for x in LEADS_BASE])))
    empresa_f = st.multiselect("Filtrar Empresa", lista_empresas)
    
    if st.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

# --- LÓGICA DE FILTRO ---
leads_filtrados = LEADS_BASE
if busca:
    leads_filtrados = [l for l in leads_filtrados if busca.lower() in l['nome'].lower()]
if empresa_f:
    leads_filtrados = [l for l in leads_filtrados if l['empresa'] in empresa_f]

# --- INTERFACE PRINCIPAL ---
st.title("🚀 Artefact Strategy")

if not leads_filtrados:
    st.warning("Nenhum lead encontrado com esses filtros.")
else:
    # Seleção de Lead (UX Melhorada)
    nomes_leads = [f"{l['nome']} ({l['empresa']})" for l in leads_filtrados]
    selecionado_nome = st.selectbox("Selecione o Lead para trabalhar:", nomes_leads)
    
    # Encontra o objeto do lead selecionado
    lead = next(l for l in leads_filtrados if f"{l['nome']} ({l['empresa']})" == selecionado_nome)
    
    st.divider()
    
    # Layout em Colunas para Detalhes
    col_info, col_action = st.columns([2, 1])
    
    with col_info:
        st.header(lead['nome'])
        st.subheader(f"{lead['cargo']} @ {lead['empresa']}")
        st.write(f"**Tomador de Decisão:** {lead['decisor']}")
    
    with col_action:
        st.link_button("🔥 Abrir LinkedIn", lead['linkedin'], use_container_width=True)

    # SISTEMA DE ABAS (UX de App Profissional)
    tab_notas, tab_historico = st.tabs(["✍️ Nova Anotação", "📜 Histórico de Contato"])
    
    with tab_notas:
        txt_nota = st.text_area("O que foi falado nessa interação?", height=150, key=f"note_{lead['id']}")
        if st.button("💾 Salvar Documentário", use_container_width=True):
            if txt_nota:
                nova_n = {
                    "id_lead": lead['id'],
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "texto": txt_nota
                }
                notas_globais.append(nova_n)
                with st.spinner("Sincronizando com GitHub..."):
                    salvar_nota(repo, notas_globais, sha_banco)
                st.success("Documentário salvo!")
                st.rerun()
            else:
                st.warning("O campo está vazio.")

    with tab_historico:
        notas_lead = [n for n in notas_globais if n.get('id_lead') == lead['id']]
        if not notas_lead:
            st.info("Ainda não há registros para este lead.")
        else:
            for n in reversed(notas_lead):
                with st.container():
                    st.caption(f"📅 {n['data']}")
                    st.write(n['texto'])
                    st.divider()
