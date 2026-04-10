import streamlit as st
import json
from github import Github
from datetime import datetime
import hmac
import time
import pandas as pd
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Artefact Strategy CRM", layout="wide", initial_sidebar_state="expanded")

# ⚠️ COLOQUE O SEU REPOSITÓRIO REAL AQUI
NOME_DO_REPOSITORIO = "fredericogalhardi-gif/mvp-artefact" 

# --- 2. LÓGICA DE TIER E LEITURA DE PLANILHA ---
def calcular_tier(score):
    try:
        score = float(score)
        if score >= 48:
            return "Tier 1"
        elif score >= 39:
            return "Tier 2"
        elif score >= 20:
            return "Tier 3"
        else:
            return "Tier 4"
    except:
        return "Tier 4" # Caso a célula esteja vazia ou com erro

@st.cache_data
def carregar_base_de_dados():
    arquivo_csv = "base_leads.csv"
    
    # Se a planilha existir no GitHub, o app lê ela!
    if os.path.exists(arquivo_csv):
        try:
            # O pandas descobre sozinho se é separado por vírgula ou ponto e vírgula
            df = pd.read_csv(arquivo_csv, sep=None, engine='python')
            
            # Normaliza os cabeçalhos (tudo minúsculo para não dar erro de digitação)
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            leads_processados = []
            for idx, row in df.iterrows():
                # Tenta puxar o score, convertendo vírgula pra ponto se precisar
                try:
                    score_str = str(row.get('score', 0)).replace(',', '.')
                    score_val = float(score_str)
                except:
                    score_val = 0

                lead_obj = {
                    "id": f"lead_csv_{idx}",
                    "nome": str(row.get('nome', row.get('name', 'Nome não informado'))),
                    "empresa": str(row.get('empresa', row.get('company', 'Empresa não informada'))),
                    "cargo": str(row.get('cargo', row.get('title', 'N/I'))),
                    "decisor": str(row.get('decisor', 'N/I')),
                    "linkedin": str(row.get('linkedin', row.get('url', '#'))),
                    "score": score_val,
                    "investimentos": str(row.get('investimentos', row.get('investimento', 'N/I'))),
                    "tier": calcular_tier(score_val),
                    "outros": "Importado via planilha automática."
                }
                leads_processados.append(lead_obj)
            return leads_processados
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return []
    else:
        # Fallback de aviso caso você ainda não tenha subido o arquivo
        return []

# Carrega a base
LEADS_BASE = carregar_base_de_dados()

# --- 3. FUNÇÕES DE SEGURANÇA (ANTI-HACK) ---
def check_login(user, pwd):
    val_user = st.secrets.get("APP_USER", "BLOQUEADO")
    val_pass = st.secrets.get("APP_PASS", "BLOQUEADO")

    user_match = hmac.compare_digest(user, val_user)
    pwd_match = hmac.compare_digest(pwd, val_pass)

    if not (user_match and pwd_match):
        time.sleep(1.5)
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
    st.title("🔐 Artefact CRM")
    with st.container():
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if check_login(user_input, pass_input):
                st.session_state.logado = True
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
    st.title("🎯 Filtros")
    
    if not LEADS_BASE:
        st.warning("⚠️ Planilha 'base_leads.csv' não encontrada no GitHub!")
    else:
        busca_nome = st.text_input("Buscar por nome")
        
        todas_empresas = sorted(list(set([x['empresa'] for x in LEADS_BASE])))
        filtro_empresa = st.multiselect("Filtrar por Empresa", todas_empresas)
        
        todos_tiers = ["Tier 1", "Tier 2", "Tier 3", "Tier 4"]
        filtro_tier = st.multiselect("Filtrar por Tier", todos_tiers)
        
    st.divider()
    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

# APLICAÇÃO DOS FILTROS
if not LEADS_BASE:
    st.title("🚀 Artefact Strategy CRM")
    st.info("Para ver seus contatos, renomeie sua planilha para 'base_leads.csv' e faça o upload no seu repositório do GitHub.")
    st.stop()

leads_exibicao = LEADS_BASE
if busca_nome:
    leads_exibicao = [l for l in leads_exibicao if busca_nome.lower() in l['nome'].lower()]
if filtro_empresa:
    leads_exibicao = [l for l in leads_exibicao if l['empresa'] in filtro_empresa]
if filtro_tier:
    leads_exibicao = [l for l in leads_exibicao if l['tier'] in filtro_tier]

# CONTEÚDO PRINCIPAL
st.title("🚀 Artefact Strategy CRM")

if not leads_exibicao:
    st.warning("Nenhum lead encontrado com os filtros atuais.")
else:
    # UX: Selectbox mostra o Tier na frente
    opcoes_formatadas = [f"[{l['tier']}] {l['nome']} ({l['empresa']})" for l in leads_exibicao]
    selecao = st.selectbox("Selecione um perfil para detalhar:", opcoes_formatadas)
    
    lead = next(l for l in leads_exibicao if f"[{l['tier']}] {l['nome']} ({l['empresa']})" == selecao)
    
    st.divider()

    # Informações em Destaque
    c1, c2 = st.columns([3, 1])
    with c1:
        st.header(lead['nome'])
        st.markdown(f"**🏢 Empresa:** {lead['empresa']}")
        st.markdown(f"**⭐ Tier:** {lead['tier']} *(Score: {lead['score']})*")
        st.markdown(f"**💰 Investimentos:** {lead['investimentos']}")
    with c2:
        # Se tiver um link válido, mostra o botão
        if str(lead['linkedin']) != "nan" and len(str(lead['linkedin'])) > 5:
            st.link_button("🔗 Ver Perfil no LinkedIn", str(lead['linkedin']), use_container_width=True)

    # Informações Ocultas
    with st.expander("👁️ Ver mais detalhes sobre o lead"):
        st.markdown(f"**💼 Cargo:** {lead['cargo']}")
        st.markdown(f"**⚖️ Decisor:** {lead['decisor']}")

    # SISTEMA DE ABAS (DOCUMENTÁRIO E HISTÓRICO)
    st.divider()
    tab_doc, tab_hist = st.tabs(["✍️ Documentário", "📜 Histórico Completo"])

    with tab_doc:
        st.markdown("### Adicionar ao Documentário")
        nova_entrada = st.text_area("Descreva a interação ou observação:", height=200)
        
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
        historico_lead = [n for n in notas_globais if n.get('id_lead') == lead['id']]
        
        if not historico_lead:
            st.info("Ainda não há registros no documentário deste lead.")
        else:
            for n in reversed(historico_lead):
                with st.container():
                    st.caption(f"📅 Registrado em: {n['data']}")
                    st.info(n['texto'])
                    st.divider()
