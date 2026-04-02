import streamlit as st
import json
from github import Github
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Artefact MVP", layout="centered")

USUARIO_ID = "admin"
SENHA_ACESSO = "123456"

# ⚠️ ALTERE AQUI PARA O SEU USUÁRIO E O NOME DO SEU REPOSITÓRIO NO GITHUB
NOME_DO_REPOSITORIO = "seu-usuario-do-github/mvp-artefact" 

# --- CONEXÃO COM O GITHUB (NOSSO BANCO DE DADOS) ---
@st.cache_resource
def conectar_github():
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(NOME_DO_REPOSITORIO)
        return repo
    except Exception as e:
        st.error(f"Erro ao conectar no GitHub. Verifique o nome do repositório e o Token.")
        return None

def carregar_notas(repo):
    try:
        # Tenta ler o arquivo banco.json do GitHub
        arquivo = repo.get_contents("banco.json")
        dados = json.loads(arquivo.decoded_content.decode("utf-8"))
        return dados, arquivo.sha
    except:
        # Se o arquivo não existir ainda, retorna uma lista vazia
        return [], None

def salvar_nota_no_github(repo, dados, sha_atual):
    novo_conteudo = json.dumps(dados, indent=4)
    if sha_atual:
        # Se o arquivo já existe, atualiza ele
        repo.update_file("banco.json", "App adicionou uma nova nota", novo_conteudo, sha_atual)
    else:
        # Se o arquivo não existe, cria pela primeira vez
        repo.create_file("banco.json", "Criando banco de dados", novo_conteudo)

# Inicia a conexão
repo = conectar_github()

# --- LÓGICA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Acesso Artefact")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if user == USUARIO_ID and pwd == SENHA_ACESSO:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")
else:
    # --- APP LOGADO ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🚀 Artefact Strategy")
    with col2:
        if st.button("Sair", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    st.divider()

    # Dados do Contato
    nome_contato = "Frederico Galhardi Borges"
    status = "Não para tomador de decisão"
    empresa = "Artefact"
    link_linkedin = "https://www.linkedin.com/feed/update/urn:li:activity:7398823203906928642/"

    st.subheader(f"👤 {nome_contato}")
    st.info(f"**Empresa:** {empresa} | **Status:** {status}")
    st.link_button("Abrir Perfil no LinkedIn", link_linkedin)

    # Puxa as notas atuais do GitHub
    if repo:
        notas_atuais, sha_arquivo = carregar_notas(repo)
    else:
        notas_atuais, sha_arquivo = [], None

    # --- ÁREA DE SALVAR NOTAS ---
    st.markdown("### Adicionar Anotação")
    nova_nota = st.text_area("Escreva aqui os detalhes da conversa:", key="input_nota")

    if st.button("💾 Salvar para sempre"):
        if repo:
            if nova_nota.strip() == "":
                st.warning("Escreva algo antes de salvar!")
            else:
                with st.spinner("Salvando no GitHub..."):
                    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    # Cria o pacote de dados da nota
                    nova_entrada = {
                        "data": agora,
                        "contato": nome_contato,
                        "texto": nova_nota
                    }
                    
                    # Adiciona a nota nova na lista e salva
                    notas_atuais.append(nova_entrada)
                    salvar_nota_no_github(repo, notas_atuais, sha_arquivo)
                    
                    st.success("Nota salva com sucesso!")
                    st.rerun() # Atualiza a tela
        else:
            st.error("Sem conexão com o repositório.")

    # --- HISTÓRICO DE NOTAS (Aparece embaixo) ---
    st.divider()
    st.markdown("### 📝 Histórico de Notas")
    
    notas_deste_contato = [n for n in notas_atuais if n.get("contato") == nome_contato]
    
    if len(notas_deste_contato) == 0:
        st.write("Nenhuma nota salva ainda.")
    else:
        # Inverte a lista para a mais nova ficar em cima
        for nota in reversed(notas_deste_contato):
            st.caption(f"🗓️ *Salvo em: {nota['data']}*")
            st.success(nota['texto'])
