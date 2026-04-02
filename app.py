import streamlit as st

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Artefact MVP", layout="centered")

# Defina seu login e senha
USUARIO_ID = "admin"
SENHA_ACESSO = "123456"

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
    st.title("🚀 Artefact Strategy")
    
    if st.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    st.divider()

    # Dados do Contato
    nome = "Frederico Galhardi Borges"
    status = "Não para tomador de decisão"
    empresa = "Artefact"
    link_linkedin = "https://www.linkedin.com/feed/update/urn:li:activity:7398823203906928642/"

    # Interface do Card
    with st.container():
        st.subheader(f"👤 {nome}")
        st.info(f"**Empresa:** {empresa} | **Status:** {status}")
        st.link_button("Abrir Perfil no LinkedIn", link_linkedin)

        # Espaço para comentário (armazenado apenas nesta sessão)
        if 'meu_comentario' not in st.session_state:
            st.session_state['meu_comentario'] = ""

        nota = st.text_area("Minhas anotações sobre ele:", value=st.session_state['meu_comentario'])

        if st.button("Salvar Nota (Temporário)"):
            st.session_state['meu_comentario'] = nota
            st.success("Nota salva para esta sessão!")
