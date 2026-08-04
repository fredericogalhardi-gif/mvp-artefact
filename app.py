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

INITIAL_LEADS = [
    {
        "ID": 1, "Nome": "Giuliane Paulista", "Empresa": "Banco do Brasil", "Cargo": "AI & Analytics Executive", 
        "LinkedIn": "https://www.linkedin.com/in/giulianepaulista/", "Prioritario": False, "Podcast": True,
        "Tema": "Construindo confiança na Era da IA: Jornada do Banco do Brasil em governança, capacitação e maturidade", 
        "Descricao": "- Estratégias para construir governança de dados e IA em escala: como estruturar um modelo de governança sólido em uma instituição do porte do Banco do Brasil\n\n- Os caminhos para alfabetizar em dados e IA milhares de colaboradores com diferentes níveis de maturidade, transformando resistência em engajamento.\n\n- Quais métricas e marcos práticos ajudam a avaliar se a organização está evoluindo de forma madura, segura e alinhada às exigências regulatórias do setor financeiro.\n\n- Como o Banco do Brasil equilibra o entusiasmo com novos modelos de IA e a necessidade de garantir respostas confiáveis, transparentes e sem alucinações.\n\n- Reflexões sobre como valores fundamentais de gestão — como resiliência, simplicidade e curiosidade — se mantêm atuais em meio a transformações tecnológicas tão aceleradas.", 
        "Status": "whatsapp não enviado"
    },
    {
        "ID": 2, "Nome": "Sara Sitta e Fernanda Vargas", "Empresa": "Ford", "Cargo": "AI & Data Science Lead (Sara)", 
        "LinkedIn": "https://www.linkedin.com/in/sarasitta/", "Prioritario": False, "Podcast": True,
        "Tema": "Fast Cases — Dados, IA, pessoas e ROI em empresas brasileiras / Workshop \"Do piloto ao P&L\" / Mesas Colaborativas", 
        "Descricao": "- Como identificar rapidamente oportunidades de Dados e IA na indústria que tenham ciclo curto de implementação e forte potencial de retorno financeiro.\n\n- Quais são os principais gargalos ao mover projetos da fase de testes para a operação diária e como garantir que o ROI seja refletido no balanço financeiro.\n\n- Como definir KPIs claros e atribuir valor financeiro a iniciativas de Inteligência Artificial (de modelos tradicionais a GenAI) \n\n- Como construir uma base de dados sólida e pipelines resilientes para garantir que as aplicações de GenAI operem com dados de alta qualidade e em escala.\n\n- Como ecossistemas abertos de discussão e compartilhamento de casos reais entre empresas brasileiras ajudam a acelerar a maturidade do mercado local de IA.", 
        "Status": "whatsapp não enviado"
    },
    {
        "ID": 3, "Nome": "Gabriel Vernalha Ribeiro", "Empresa": "Dasa", "Cargo": "Executivo de Dados, Analytics e IA", 
        "LinkedIn": "https://www.linkedin.com/in/gvribeiro/", "Prioritario": False, "Podcast": True,
        "Tema": "Liderando o Futuro / Board Reverse Pitch: A IA muda tudo? / Mesas Colaborativas", 
        "Descricao": "- Como liderar a agenda de implementação da IA em um ecossistema tão crítico e regulado quanto o de saúde.\n\n- Como conduzir a conversa com conselheiros e acionistas sem cair no exagero do hype, balanceando grandes promessas com retorno claro de investimento, gestão de riscos e segurança do paciente.\n\n- Estratégias práticas para manter a conformidade (LGPD/hipaa), a privacidade de dados médicos e a qualidade analítica sem travar a inovação\n\n- Como aplicar PMO, OKRs e Design Thinking para gerenciar a carteira de projetos de inteligência artificial, priorizando as iniciativas que trazem maior impacto nos resultados e na jornada do cliente/paciente.\n\n- Como engajar e capacitar equipes multidisciplinares e profissionais da saúde — que muitas vezes resistem à automação —, promovendo a adoção confiável de novas ferramentas.", 
        "Status": "whatsapp não enviado"
    },
    {
        "ID": 4, "Nome": "Gabriel Mochnacs", "Empresa": "Cielo", "Cargo": "Superintendente de Dados e IA", 
        "LinkedIn": "https://www.linkedin.com/in/gabrielmarruda/", "Prioritario": False, "Podcast": True,
        "Tema": "O que ninguém conta sobre escalar IA: falhas, dados, governança e as decisões que fazem pilotos virarem negócio", 
        "Descricao": "- Quais são os principais motivos que fazem projetos promissores falharem e o que a dor da tentativa ensina sobre maturidade de dados.\n\n- Quais decisões técnicas, de governança e de arquitetura precisam ser tomadas no \"dia zero\" para garantir que uma prova de conceito consiga suportar o volume de um gigante de pagamentos como a Cielo.\n\n- A importância de construir capacidades sólidas de observabilidade e arquitetura em nuvem para sustentar modelos avançados de IA sem explodir custos operacionais nem degradar a qualidade dos dados.\n\n- Como conduzir a mudança cultural necessária para que as áreas de negócio realmente adotem e confiem na tomada de decisão orientada por IA.\n\n- Como a educação executiva recente em GenAI ajuda a filtrar o hype e a tomar decisões pragmáticas para construir o modelo operacional das empresas líderes do mercado", 
        "Status": "whatsapp não enviado"
    },
    {
        "ID": 5, "Nome": "Gustavo Nery", "Empresa": "Anatel", "Cargo": "CIO", 
        "LinkedIn": "https://www.linkedin.com/in/gustavo-nery-silva/", "Prioritario": False, "Podcast": True,
        "Tema": "O que ninguém conta sobre escalar IA: falhas, dados, governança e as decisões que fazem pilotos virarem negócio", 
        "Descricao": "- Os gargalos invisíveis e burocráticos de infraestrutura, dados e compras públicas que dificultam que soluções de IA saiam do papel e virem serviço público.\n\n- Como lidar com as falhas inerentes aos modelos de IA em um ambiente estatal onde a transparência e a responsabilidade legal são exigências absolutas perante órgãos de controle e a sociedade.\n\n- TransformaGov e a virada para a gestão pública orientada a dados: lições aprendidas em grandes programas de transformação do Estado que ajudam a desenhar processos para que a IA seja uma alavanca de produtividade e não apenas um hype.\n\n- Como estruturar modelos de governança, interoperabilidade e compartilhamento de dados sensíveis entre diferentes áreas e órgãos federais para viabilizar projetos robustos de IA.\n\n- As dores e aprendizados de usar internamente na agência reguladora as mesmas tecnologias de inteligência artificial que essa mesma agência precisa regular para o mercado de telecomunicações.", 
        "Status": "whatsapp não enviado"
    },
    {
        "ID": 6, "Nome": "Sabrina Nazario", "Empresa": "Schneider electric", "Cargo": "CDO SAM", 
        "LinkedIn": "https://www.linkedin.com/in/sabrina-nazario-7138a822/", "Prioritario": False, "Podcast": True,
        "Tema": "Governança e Estratégia de Dados na América do Sul: Desafios e Escala Regional", 
        "Descricao": "- Os desafios de desenhar e implementar uma estratégia de dados coesa para toda LATAM, considerando as particularidades locais e as diretrizes globais de uma empresa gigante como a Schneider Electric.\n\n- Como estruturar uma governança de dados eficiente que garanta qualidade, conformidade e segurança sem criar burocracia excessiva ou travar a agilidade e a inovação das equipes.\n\n- Quais estratégias e iniciativas práticas têm sido mais eficazes para vencer a resistência à mudança, democratizar o acesso à informação e elevar a maturidade analítica dos times operacionais e executivos.\n\n- Como a Schneider Electric está utilizando dados e IA para impulsionar soluções de eficiência energética, sustentabilidade e automação industrial na América do Sul.", 
        "Status": "whatsapp não enviado"
    },
    {'Cargo': 'CEO', 'Descricao': '', 'Empresa': '5Era', 'ID': 7, 'LinkedIn': '', 'Nome': 'GIL GIARDELLI', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Superintendente de Tecnologia', 'Descricao': '', 'Empresa': 'A5X', 'ID': 8, 'LinkedIn': '', 'Nome': 'Cleverson Arashiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de Dados', 'Descricao': '', 'Empresa': 'Aché', 'ID': 9, 'LinkedIn': '', 'Nome': 'Dianne Sheila Salviano', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Sistemas', 'Descricao': '', 'Empresa': 'Aché', 'ID': 10, 'LinkedIn': '', 'Nome': 'Ronaldo Canteiro Conceição', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Ciência de Dados', 'Descricao': '', 'Empresa': 'AFYA SAO PAULO', 'ID': 11, 'LinkedIn': '', 'Nome': 'Leandro Carnevali', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Operações de TI', 'Descricao': '', 'Empresa': 'AGENCIA ESTADO', 'ID': 12, 'LinkedIn': '', 'Nome': 'Reynaldo Rancan', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sócio', 'Descricao': '', 'Empresa': 'ai2c', 'ID': 13, 'LinkedIn': '', 'Nome': 'Daniel Serman', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Member Board', 'Descricao': '', 'Empresa': 'AIDL', 'ID': 14, 'LinkedIn': '', 'Nome': 'Rosane Ricciardi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente nacional vendas', 'Descricao': '', 'Empresa': 'ALLERGAN AESTHETICS', 'ID': 15, 'LinkedIn': '', 'Nome': 'FERNANDA MORAES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Dados & IA', 'Descricao': '', 'Empresa': 'Alloha Fibra', 'ID': 16, 'LinkedIn': '', 'Nome': 'Flavio Fonseca de Souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Engenharia e Dados', 'Descricao': '', 'Empresa': 'ALLOS', 'ID': 17, 'LinkedIn': '', 'Nome': 'Thiago Barcellos Costa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GLOBAL DATA & AI DIRECTOR', 'Descricao': '', 'Empresa': 'ALPARGATAS', 'ID': 18, 'LinkedIn': '', 'Nome': 'DIOGENES JUSTO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'Alper Seguros', 'ID': 19, 'LinkedIn': '', 'Nome': 'Diego Santana', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Data', 'Descricao': '', 'Empresa': 'Amazon', 'ID': 20, 'LinkedIn': '', 'Nome': 'Carina Ameijeiras', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Al Director', 'Descricao': '', 'Empresa': 'AMBEV', 'ID': 21, 'LinkedIn': '', 'Nome': 'Patricia Camargo Kristman', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Ambev', 'ID': 22, 'LinkedIn': '', 'Nome': 'Victor Marcel', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Data & Analytics', 'Descricao': '', 'Empresa': 'Ambev', 'ID': 23, 'LinkedIn': '', 'Nome': 'Wescley Trajano Soares', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE DE DADOS', 'Descricao': '', 'Empresa': 'AMBEV TECH', 'ID': 24, 'LinkedIn': '', 'Nome': 'FÁBIA S LIMEIRA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sr Manager', 'Descricao': '', 'Empresa': 'Ambev Tech', 'ID': 25, 'LinkedIn': '', 'Nome': 'Rafael Cordeiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente SR de Dados & IA', 'Descricao': '', 'Empresa': 'Amil', 'ID': 26, 'LinkedIn': '', 'Nome': 'Helinton Fediuk', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Dados & IA', 'Descricao': '', 'Empresa': 'Anbima', 'ID': 27, 'LinkedIn': '', 'Nome': 'Catia Guedes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Administradora de Dados', 'Descricao': '', 'Empresa': 'ANS', 'ID': 28, 'LinkedIn': '', 'Nome': 'Werônica dos Santos Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Смо', 'Descricao': '', 'Empresa': 'Artefact', 'ID': 29, 'LinkedIn': '', 'Nome': 'Manuela Ponfick', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE DE TRANSFORMAÇÃO', 'Descricao': '', 'Empresa': 'ARTERIS', 'ID': 30, 'LinkedIn': '', 'Nome': 'MAURICIO CESAR VITORINO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Dados & Al', 'Descricao': '', 'Empresa': 'ASA', 'ID': 31, 'LinkedIn': '', 'Nome': 'Gerardo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Governance Leader', 'Descricao': '', 'Empresa': 'Asaas', 'ID': 32, 'LinkedIn': '', 'Nome': 'Sarine Azevedo Aguiar de Albuquerque', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de TI', 'Descricao': '', 'Empresa': 'Assaí Atacadista', 'ID': 33, 'LinkedIn': '', 'Nome': 'Paulo Cesar Coelho Ribeiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'QA Engineer', 'Descricao': '', 'Empresa': 'Atech', 'ID': 34, 'LinkedIn': '', 'Nome': 'Vinícius Olice Ramalho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Desenvolvimento Tech', 'Descricao': '', 'Empresa': 'Atmo Energia', 'ID': 35, 'LinkedIn': '', 'Nome': 'Victor Romano', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Dados', 'Descricao': '', 'Empresa': 'Atvos', 'ID': 36, 'LinkedIn': '', 'Nome': 'Diego Antonio Freire Dias', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Exec de Tecnologia', 'Descricao': '', 'Empresa': 'Atvos', 'ID': 37, 'LinkedIn': '', 'Nome': 'Luiza Junqueira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head IA', 'Descricao': '', 'Empresa': 'Atvos', 'ID': 38, 'LinkedIn': '', 'Nome': 'Michel Rudan Isaias Vargas', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Al Citizen Partner', 'Descricao': '', 'Empresa': 'Auren', 'ID': 39, 'LinkedIn': '', 'Nome': 'Dilson Shinye', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'AUTOGLASS', 'ID': 40, 'LinkedIn': '', 'Nome': 'BRUNO SALVAREZ PESTANA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de Dados', 'Descricao': '', 'Empresa': 'AUTOGLASS', 'ID': 41, 'LinkedIn': '', 'Nome': 'João Igor Francisco Rosi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Analytics', 'Descricao': '', 'Empresa': 'Beltrão', 'ID': 42, 'LinkedIn': '', 'Nome': 'BELTRÃO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Senior Data Engineer', 'Descricao': '', 'Empresa': 'Betnacional', 'ID': 43, 'LinkedIn': '', 'Nome': 'Luis Felipe Almeida Nogueira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretoria de Dados e TI', 'Descricao': '', 'Empresa': 'BFFC', 'ID': 44, 'LinkedIn': '', 'Nome': 'Fernanda Rimbano', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de TI', 'Descricao': '', 'Empresa': 'Blanver', 'ID': 45, 'LinkedIn': '', 'Nome': 'Ivo Mello', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de dados e IA', 'Descricao': '', 'Empresa': 'BLAU', 'ID': 46, 'LinkedIn': '', 'Nome': 'Bruno Dell Agli', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Fundador', 'Descricao': '', 'Empresa': 'BLOOMING Negocios', 'ID': 47, 'LinkedIn': '', 'Nome': 'Rodrigo Rangel de Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Data', 'Descricao': '', 'Empresa': 'Blue3', 'ID': 48, 'LinkedIn': '', 'Nome': 'jailson rainer da silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Arquitetura', 'Descricao': '', 'Empresa': 'BNPP CARDIF', 'ID': 49, 'LinkedIn': '', 'Nome': 'Ricardo de Carvalho Destro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Data Science', 'Descricao': '', 'Empresa': 'BOCOM BBM', 'ID': 50, 'LinkedIn': '', 'Nome': 'Lucas Costa Favaro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista de Dados e IA', 'Descricao': '', 'Empresa': 'Bracell', 'ID': 51, 'LinkedIn': '', 'Nome': 'Gustavo Bortolotti Barbosa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Specialist', 'Descricao': '', 'Empresa': 'Bracell BSP', 'ID': 52, 'LinkedIn': '', 'Nome': 'Érico Mendes Domingues', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista Comercial', 'Descricao': '', 'Empresa': 'BRADESCO', 'ID': 53, 'LinkedIn': '', 'Nome': 'Alessandro de Freitas', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Surperintendente Sr', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 54, 'LinkedIn': '', 'Nome': 'Daniel Rodamilans', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Engineer Tech Manager', 'Descricao': '', 'Empresa': 'BRADESCO', 'ID': 55, 'LinkedIn': '', 'Nome': 'Felipe Macedo de Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Science Manager', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 56, 'LinkedIn': '', 'Nome': 'Tatiane Casanova Penteado', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Engineer Manager', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 57, 'LinkedIn': '', 'Nome': 'Thiago Luiz Milagres de Paula', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sr Manager', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 58, 'LinkedIn': '', 'Nome': 'Vanessa Ramalho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Engineer Manager', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 59, 'LinkedIn': '', 'Nome': 'Patricio Molina', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Data & Al', 'Descricao': '', 'Empresa': 'Bradesco', 'ID': 60, 'LinkedIn': '', 'Nome': 'Igor Costa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente SR', 'Descricao': '', 'Empresa': 'BRADESCO EST UNIF', 'ID': 61, 'LinkedIn': '', 'Nome': 'Augusto Vieira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista de planejamento Comer', 'Descricao': '', 'Empresa': 'BRADESCO EST UNIF', 'ID': 62, 'LinkedIn': '', 'Nome': 'Bruna Thamara Zolotareff', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Sr', 'Descricao': '', 'Empresa': 'BRADESCO EST UNIF', 'ID': 63, 'LinkedIn': '', 'Nome': 'Robson Gonçalves da Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sr Analytics Manager', 'Descricao': '', 'Empresa': 'BRASIL PLURAL', 'ID': 64, 'LinkedIn': '', 'Nome': 'Mateus Rodrigues Braga Nascimento', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'Bravo Serviços Logísticos', 'ID': 65, 'LinkedIn': '', 'Nome': 'João Marcos Barroso Lacerda', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Specialist', 'Descricao': '', 'Empresa': 'Brookfield', 'ID': 66, 'LinkedIn': '', 'Nome': 'MARCOS CACERES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Audit Analytics & AI SVP', 'Descricao': '', 'Empresa': 'Brookfield Asset Management', 'ID': 67, 'LinkedIn': '', 'Nome': 'Marcos Roberto Pereira Kovacs', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Executive Director', 'Descricao': '', 'Empresa': 'BTG PACTUAL', 'ID': 68, 'LinkedIn': '', 'Nome': 'Carlos Henrique Feiteira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Associate director', 'Descricao': '', 'Empresa': 'BTG PACTUAL', 'ID': 69, 'LinkedIn': '', 'Nome': 'Gustavo Zenzo Shibukawa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Data science COE', 'Descricao': '', 'Empresa': 'Bunge', 'ID': 70, 'LinkedIn': '', 'Nome': 'FELIPE MIANA DE FARIA FURTADO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Comercial', 'Descricao': '', 'Empresa': 'Bunge', 'ID': 71, 'LinkedIn': '', 'Nome': 'Rafael Fini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Global Enterp. Data Architect', 'Descricao': '', 'Empresa': 'BUNGE', 'ID': 72, 'LinkedIn': '', 'Nome': 'Ronaldo Braghittoni', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista de Analytics', 'Descricao': '', 'Empresa': 'Bunge', 'ID': 73, 'LinkedIn': '', 'Nome': 'André Pimenta', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'CABERGS', 'ID': 74, 'LinkedIn': '', 'Nome': 'Vitor Hugo Hoffmann da Costa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'Caju', 'ID': 75, 'LinkedIn': '', 'Nome': 'Marcelo Hiroshi Ogava', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de B.I.', 'Descricao': '', 'Empresa': 'Campari do Brasil', 'ID': 76, 'LinkedIn': '', 'Nome': 'Carlos Eduardo Estácio', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Specialist', 'Descricao': '', 'Empresa': 'Campari do Brasil LTDA', 'ID': 77, 'LinkedIn': '', 'Nome': 'Pedro Ticiani dos Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista IA', 'Descricao': '', 'Empresa': 'Care Plus', 'ID': 78, 'LinkedIn': '', 'Nome': 'Juliana Fidelis', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de Dados', 'Descricao': '', 'Empresa': 'Care plus', 'ID': 79, 'LinkedIn': '', 'Nome': 'Iris Sachimoto', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Ger. Data Analytics & Strategy', 'Descricao': '', 'Empresa': 'Care Plus', 'ID': 80, 'LinkedIn': '', 'Nome': 'THIAGO SATO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente SR IA', 'Descricao': '', 'Empresa': 'Care Plus Bupa', 'ID': 81, 'LinkedIn': '', 'Nome': 'Renato Rossi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Compliance Proteção de Dados', 'Descricao': '', 'Empresa': 'Cartão Elo', 'ID': 82, 'LinkedIn': '', 'Nome': 'Talita Mariana dos Santos Caputo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CDAIO', 'Descricao': '', 'Empresa': 'Casas Bahia', 'ID': 83, 'LinkedIn': '', 'Nome': 'Guilherme Augusto Lopes Ferreira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Dados & Analytics', 'Descricao': '', 'Empresa': 'CBMM', 'ID': 84, 'LinkedIn': '', 'Nome': 'Luciano Cassita', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Financeiro', 'Descricao': '', 'Empresa': 'CENTER NORTE', 'ID': 85, 'LinkedIn': '', 'Nome': 'Luís Fernando da Rocha Mai', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': '', 'Descricao': '', 'Empresa': 'Certisign', 'ID': 86, 'LinkedIn': '', 'Nome': 'Renan Roberto dos Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Analytics Manager', 'Descricao': '', 'Empresa': 'Chubb Seguros', 'ID': 87, 'LinkedIn': '', 'Nome': 'Luis Esteban Cueva Ayala', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de Tecnologia', 'Descricao': '', 'Empresa': 'Cidade Center Norte', 'ID': 88, 'LinkedIn': '', 'Nome': 'Adelle Bueno Dantas', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Arquitetura', 'Descricao': '', 'Empresa': 'CIEE', 'ID': 89, 'LinkedIn': '', 'Nome': 'Patricia Cardoso', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sup. Exec. Dados e IA', 'Descricao': '', 'Empresa': 'Cielo', 'ID': 90, 'LinkedIn': '', 'Nome': 'Gabriel Mochnacs', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Inovação', 'Descricao': '', 'Empresa': 'Claro', 'ID': 91, 'LinkedIn': '', 'Nome': 'Denise Nunes Pithan', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Ger Recursos Humanos', 'Descricao': '', 'Empresa': 'Claro', 'ID': 92, 'LinkedIn': '', 'Nome': 'Eliane Lopes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Infraestrutura TI', 'Descricao': '', 'Empresa': 'Claro', 'ID': 93, 'LinkedIn': '', 'Nome': 'Fernando Navarro de Castro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretora do CoE Al', 'Descricao': '', 'Empresa': 'Claro', 'ID': 94, 'LinkedIn': '', 'Nome': 'Livia Almeida', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Plataformas Cloud -GPM', 'Descricao': '', 'Empresa': 'Claro', 'ID': 95, 'LinkedIn': '', 'Nome': 'Roberta Altermann', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Dados & la', 'Descricao': '', 'Empresa': 'Claro', 'ID': 96, 'LinkedIn': '', 'Nome': 'RODRIGO NAZARIO CONDOLEO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'DADOS & IA', 'Descricao': '', 'Empresa': 'CLARO', 'ID': 97, 'LinkedIn': '', 'Nome': 'RODRIGO PERES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Dir. Executivo Tech Dados & IA', 'Descricao': '', 'Empresa': 'CLARO', 'ID': 98, 'LinkedIn': '', 'Nome': 'Sergio Gaiotto', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'ClickBus', 'ID': 99, 'LinkedIn': '', 'Nome': 'Cesar Augusto de Carvalho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Information', 'Descricao': '', 'Empresa': 'Coala Saúde', 'ID': 100, 'LinkedIn': '', 'Nome': 'Vinicius Possato', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Growth & CX', 'Descricao': '', 'Empresa': 'Coca Cola FEMSA', 'ID': 101, 'LinkedIn': '', 'Nome': 'Felipe Coin', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Governança Dados e IA', 'Descricao': '', 'Empresa': 'Cogna', 'ID': 102, 'LinkedIn': '', 'Nome': 'Leonardo Henrique Albuquerque de Lima', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Sênior de Arquitetura', 'Descricao': '', 'Empresa': 'Cogna', 'ID': 103, 'LinkedIn': '', 'Nome': 'Daniel Rosa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Ger. Engenharia do Aprendizado', 'Descricao': '', 'Empresa': 'Cogna Educação', 'ID': 104, 'LinkedIn': '', 'Nome': 'Mario Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sócio | Diretor de Engenharia', 'Descricao': '', 'Empresa': 'Cogna Educação', 'ID': 105, 'LinkedIn': '', 'Nome': 'Tercio Alves da Rocha Filho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Produtos Digitais', 'Descricao': '', 'Empresa': 'COGNA EDUCAÇÃO', 'ID': 106, 'LinkedIn': '', 'Nome': 'Tyagi Mansur Lima', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CEO', 'Descricao': '', 'Empresa': 'Colectta', 'ID': 107, 'LinkedIn': '', 'Nome': 'Rafael Adib', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Tl e Dados', 'Descricao': '', 'Empresa': 'COMGAS', 'ID': 108, 'LinkedIn': '', 'Nome': 'Thiago Trevisan', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Ciência de Dados', 'Descricao': '', 'Empresa': 'Comgás', 'ID': 109, 'LinkedIn': '', 'Nome': 'Lia Bandeira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Comgás', 'ID': 110, 'LinkedIn': '', 'Nome': 'marcelo yassuo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de TI', 'Descricao': '', 'Empresa': 'COMPANHIA SIDERURGICA NACIONAL', 'ID': 111, 'LinkedIn': '', 'Nome': 'Bruno Héctor Fernandes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Consultor Data Platform & Al', 'Descricao': '', 'Empresa': 'Conseghe Consultoria Estrategi', 'ID': 112, 'LinkedIn': '', 'Nome': 'EMERSON PRZYBYLOVIECZ', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador Ciência de Dados', 'Descricao': '', 'Empresa': 'CONSORCIO NACIONAL EMBRACON', 'ID': 113, 'LinkedIn': '', 'Nome': 'DIEGO FREGONESI HERNANDES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de BI', 'Descricao': '', 'Empresa': 'CONSORCIO NACIONAL EMBRACON', 'ID': 114, 'LinkedIn': '', 'Nome': 'FRANCISCO ALMIR DE SOUZA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Inteligência de dados', 'Descricao': '', 'Empresa': 'CONSORCIO NACIONAL EMBRACON', 'ID': 115, 'LinkedIn': '', 'Nome': 'João Martello', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretora de Tecnologia LATAM', 'Descricao': '', 'Empresa': 'Corteva', 'ID': 116, 'LinkedIn': '', 'Nome': 'Juliana Cirillo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Work Process and Data Leader', 'Descricao': '', 'Empresa': 'Corteva Agriscience', 'ID': 117, 'LinkedIn': '', 'Nome': 'Bianca Pezel Sviantek Marya', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Business Reporting Leader', 'Descricao': '', 'Empresa': 'CORTEVA AGRISCIENCE', 'ID': 118, 'LinkedIn': '', 'Nome': 'Murilo Martins de Souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de TI', 'Descricao': '', 'Empresa': 'Crown', 'ID': 119, 'LinkedIn': '', 'Nome': 'Givaldo Soares', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de TI', 'Descricao': '', 'Empresa': 'Crown Embalagens', 'ID': 120, 'LinkedIn': '', 'Nome': 'Rodolfo Elmi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista de Dados', 'Descricao': '', 'Empresa': 'CSN', 'ID': 121, 'LinkedIn': '', 'Nome': 'Vinicius Bozzon', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de TI', 'Descricao': '', 'Empresa': 'Cushman & Wakefield', 'ID': 122, 'LinkedIn': '', 'Nome': 'Rodrigo Libano de Souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Data Analytics', 'Descricao': '', 'Empresa': 'Daki', 'ID': 123, 'LinkedIn': '', 'Nome': 'Lucas Mendes Mota da Fonseca', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Al & Data', 'Descricao': '', 'Empresa': 'Daki', 'ID': 124, 'LinkedIn': '', 'Nome': 'Marcus Bernardi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'Daki', 'ID': 125, 'LinkedIn': '', 'Nome': 'Michel Kruchin de Oliveira Lima', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Ethical DATA and Al Governance', 'Descricao': '', 'Empresa': 'DAMA BRASIL', 'ID': 126, 'LinkedIn': '', 'Nome': 'CONSUELO MILANI RODRIGUES GALANI', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'PRESIDENTE', 'Descricao': '', 'Empresa': 'DAMA BRASIL', 'ID': 127, 'LinkedIn': '', 'Nome': 'Sergio Aparecido Oliveira da Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'EXECUTIVO', 'Descricao': '', 'Empresa': 'DASA', 'ID': 128, 'LinkedIn': '', 'Nome': 'Gabriel Vernalha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de dados', 'Descricao': '', 'Empresa': 'DASA', 'ID': 129, 'LinkedIn': '', 'Nome': 'janaina lainez', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Data Analytics, VPFinance', 'Descricao': '', 'Empresa': 'DASA', 'ID': 130, 'LinkedIn': '', 'Nome': 'FELIPE MOURA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Lider Executiva', 'Descricao': '', 'Empresa': 'Data Hackers', 'ID': 131, 'LinkedIn': '', 'Nome': 'Monique Oliveira dos Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Governança de IA', 'Descricao': '', 'Empresa': 'Dataprev', 'ID': 132, 'LinkedIn': '', 'Nome': 'Alexandro Soares', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder', 'Descricao': '', 'Empresa': 'Dataprev', 'ID': 133, 'LinkedIn': '', 'Nome': 'Cirino Refosco', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE DE DIVISÃO', 'Descricao': '', 'Empresa': 'DATAPREV', 'ID': 134, 'LinkedIn': '', 'Nome': 'FERNANDO LEGEY', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista de Informações', 'Descricao': '', 'Empresa': 'Dataprev', 'ID': 135, 'LinkedIn': '', 'Nome': 'Giseli Rocha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente', 'Descricao': '', 'Empresa': 'DATAPREV', 'ID': 136, 'LinkedIn': '', 'Nome': 'Luiz Benini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de equipe I', 'Descricao': '', 'Empresa': 'DATAPREV', 'ID': 137, 'LinkedIn': '', 'Nome': 'Rodrigo Melo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder', 'Descricao': '', 'Empresa': 'Dataprev', 'ID': 138, 'LinkedIn': '', 'Nome': 'Tiago Santana', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de MKT e design', 'Descricao': '', 'Empresa': 'DATASCHOOL', 'ID': 139, 'LinkedIn': '', 'Nome': 'Léo Namem Ambros', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Comercial & Marketing', 'Descricao': '', 'Empresa': 'DATUM INFORMATICA', 'ID': 140, 'LinkedIn': '', 'Nome': 'Patricia Chermont', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Executive Senior Manager', 'Descricao': '', 'Empresa': 'Deloitte', 'ID': 141, 'LinkedIn': '', 'Nome': 'Nilton Ueda', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Data Analytics', 'Descricao': '', 'Empresa': 'Dexco', 'ID': 142, 'LinkedIn': '', 'Nome': 'Renato Xavier', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CTO', 'Descricao': '', 'Empresa': 'Diel Energia', 'ID': 143, 'LinkedIn': '', 'Nome': 'Edson Rocha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gestão da Alimentação Pública.', 'Descricao': '', 'Empresa': 'DIGIX', 'ID': 144, 'LinkedIn': '', 'Nome': 'Alex Mendes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head software engineering', 'Descricao': '', 'Empresa': 'Dimensa', 'ID': 145, 'LinkedIn': '', 'Nome': 'Alexandre Arantes Bezerra Barbosa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Analytics', 'Descricao': '', 'Empresa': 'DIRECAO GERAL', 'ID': 146, 'LinkedIn': '', 'Nome': 'Ana Carolina Oliveira Campos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Staff Data Product Manager', 'Descricao': '', 'Empresa': 'dLocal', 'ID': 147, 'LinkedIn': '', 'Nome': 'IAGO RIBEIRO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Platform Lead', 'Descricao': '', 'Empresa': 'dlocal', 'ID': 148, 'LinkedIn': '', 'Nome': 'Marcos Oliveira Junior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Digital Made Accessible Count', 'Descricao': '', 'Empresa': 'DMA', 'ID': 149, 'LinkedIn': '', 'Nome': 'Albervan Ferreira Luz', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Eng de Dados e Bl', 'Descricao': '', 'Empresa': 'DMSC', 'ID': 150, 'LinkedIn': '', 'Nome': 'Bruno Santana', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Inteligência & Dados', 'Descricao': '', 'Empresa': 'DUX Company', 'ID': 151, 'LinkedIn': '', 'Nome': 'Thiago Buselato Maurício', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Sr Manager', 'Descricao': '', 'Empresa': 'EBANX', 'ID': 152, 'LinkedIn': '', 'Nome': 'Alessandra Arduini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Riscos e Controles', 'Descricao': '', 'Empresa': 'Ecorodovias', 'ID': 153, 'LinkedIn': '', 'Nome': 'Giselle Guimarães', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Governance Specialist', 'Descricao': '', 'Empresa': 'EDENRED', 'ID': 154, 'LinkedIn': '', 'Nome': 'Alfredo Esteves Torres Garavelo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Director', 'Descricao': '', 'Empresa': 'EDENRED', 'ID': 155, 'LinkedIn': '', 'Nome': 'Lauren Tammy Hikage', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Data&Al', 'Descricao': '', 'Empresa': 'Einstein Hospital Israelita', 'ID': 156, 'LinkedIn': '', 'Nome': 'Marcos Araujo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'LIDER DOMINIO AI - DATA - DEV', 'Descricao': '', 'Empresa': 'ELIS BRAZIL', 'ID': 157, 'LinkedIn': '', 'Nome': 'ELISANGELA GOMES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Executiva Comercial', 'Descricao': '', 'Empresa': 'Elo', 'ID': 158, 'LinkedIn': '', 'Nome': 'Camila Cassemiro Esteves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Chefe de Gabinete', 'Descricao': '', 'Empresa': 'EMATER MG', 'ID': 159, 'LinkedIn': '', 'Nome': 'Elisangela Vieira de Souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Admin. e Financeiro', 'Descricao': '', 'Empresa': 'EMATER MG', 'ID': 160, 'LinkedIn': '', 'Nome': 'Everton Augusto Paiva Ferreira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE DE IA', 'Descricao': '', 'Empresa': 'EMBRAER', 'ID': 161, 'LinkedIn': '', 'Nome': 'Giuliano Neves da Silva Mendonça', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Segurança e Dad', 'Descricao': '', 'Empresa': 'EMTEL', 'ID': 162, 'LinkedIn': '', 'Nome': 'Renan Soares Pinheiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Product Manager', 'Descricao': '', 'Empresa': 'ENGIE', 'ID': 163, 'LinkedIn': '', 'Nome': 'Henrique Avelino', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE DIGITAL', 'Descricao': '', 'Empresa': 'ENGIE', 'ID': 164, 'LinkedIn': '', 'Nome': 'SAMI SHAMALI', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Data & Dev', 'Descricao': '', 'Empresa': 'EPTV', 'ID': 165, 'LinkedIn': '', 'Nome': 'Bruno Mascaro Woth', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista de Produtos', 'Descricao': '', 'Empresa': 'EPTV', 'ID': 166, 'LinkedIn': '', 'Nome': 'Roger Sena da Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'HEAD DE TI - DADOS E IA', 'Descricao': '', 'Empresa': 'ERO BRASIL PARTICIPACOES', 'ID': 167, 'LinkedIn': '', 'Nome': 'ROGERIO AUGUSTO CARVALHO SOUZA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'ERO COPPER', 'ID': 168, 'LinkedIn': '', 'Nome': 'MARCELO A. SANTOS', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'IT Manager', 'Descricao': '', 'Empresa': 'Esfera Energia', 'ID': 169, 'LinkedIn': '', 'Nome': 'Graciele Janini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Branding', 'Descricao': '', 'Empresa': 'ESTRELABET', 'ID': 170, 'LinkedIn': '', 'Nome': 'VICTOR BLECKER', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Arquiteto Especialista', 'Descricao': '', 'Empresa': 'Evertec Brasil', 'ID': 171, 'LinkedIn': '', 'Nome': 'Marcelo Paulo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Desenvolvimento', 'Descricao': '', 'Empresa': 'Evertex', 'ID': 172, 'LinkedIn': '', 'Nome': 'Alexandre Pereira Martini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Exa', 'ID': 173, 'LinkedIn': '', 'Nome': 'Eustáquio Ruvieri Junior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de Analytics', 'Descricao': '', 'Empresa': 'EXA', 'ID': 174, 'LinkedIn': '', 'Nome': 'Paloma Cristina de Souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Assessor de TIC', 'Descricao': '', 'Empresa': 'FAB', 'ID': 175, 'LinkedIn': '', 'Nome': 'Silvio Roberto Assunção de Oliveira Filho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados & Analytics', 'Descricao': '', 'Empresa': 'Farmácias São João', 'ID': 176, 'LinkedIn': '', 'Nome': 'Erick Tsukahara', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Data Science', 'Descricao': '', 'Empresa': 'Farmtech', 'ID': 177, 'LinkedIn': '', 'Nome': 'Guilherme Martins Dias Batista', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'DIRETOR DATA & ANALYTICS', 'Descricao': '', 'Empresa': 'FARMTECH', 'ID': 178, 'LinkedIn': '', 'Nome': 'RODRIGO GABRIEL RIBEIRO DE DEUS', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados', 'Descricao': '', 'Empresa': 'FARMTECH', 'ID': 179, 'LinkedIn': '', 'Nome': 'Vinicius Coelho Dos Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'DIRETOR', 'Descricao': '', 'Empresa': 'FAST SHOP', 'ID': 180, 'LinkedIn': '', 'Nome': 'MARCOS ROGÉRIO ADAM', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e IA', 'Descricao': '', 'Empresa': 'FAST SHOP', 'ID': 181, 'LinkedIn': '', 'Nome': 'Maycol Brandão', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'SUPERINTENDENTE DE TI', 'Descricao': '', 'Empresa': 'FGV', 'ID': 182, 'LinkedIn': '', 'Nome': 'Vitor Rangel', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'diretora', 'Descricao': '', 'Empresa': 'FIA', 'ID': 183, 'LinkedIn': '', 'Nome': 'Alessandra Montini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Tecnologia', 'Descricao': '', 'Empresa': 'Fleury', 'ID': 184, 'LinkedIn': '', 'Nome': 'Thiago Teixeira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Manager', 'Descricao': '', 'Empresa': 'Flutter', 'ID': 185, 'LinkedIn': '', 'Nome': 'Dani Bistafa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Senior Data Manager', 'Descricao': '', 'Empresa': 'Flutter', 'ID': 186, 'LinkedIn': '', 'Nome': 'Mirella Rodrigues', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Data Platform', 'Descricao': '', 'Empresa': 'Flutter Brazil', 'ID': 187, 'LinkedIn': '', 'Nome': 'Jorge Kennedy Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analytics Engineer', 'Descricao': '', 'Empresa': 'Flutter Brazil', 'ID': 188, 'LinkedIn': '', 'Nome': 'Vinicius Rocha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de CRM МКТ', 'Descricao': '', 'Empresa': 'Fogo de Chão', 'ID': 189, 'LinkedIn': '', 'Nome': 'Débora', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Tecnologia e Inovação', 'Descricao': '', 'Empresa': 'FONNET NETWORKS', 'ID': 190, 'LinkedIn': '', 'Nome': 'Diego Soares', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Tecnologia', 'Descricao': '', 'Empresa': 'FONNET NETWORKS', 'ID': 191, 'LinkedIn': '', 'Nome': 'Marcelo Matos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Al Arquitect', 'Descricao': '', 'Empresa': 'FORD', 'ID': 192, 'LinkedIn': '', 'Nome': 'Anderson A B Rodrigues', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Analytics & Al Manager', 'Descricao': '', 'Empresa': 'Ford', 'ID': 193, 'LinkedIn': '', 'Nome': 'Renato Carlos Lopes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'It Director', 'Descricao': '', 'Empresa': 'Ford Motor Company', 'ID': 194, 'LinkedIn': '', 'Nome': 'Fernanda Vargas', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'PMO', 'Descricao': '', 'Empresa': 'FRIBOI', 'ID': 195, 'LinkedIn': '', 'Nome': 'Valquíria Beserra', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'FSB Holding', 'ID': 196, 'LinkedIn': '', 'Nome': 'Felipe Merfa Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CDO', 'Descricao': '', 'Empresa': 'FSB Holding', 'ID': 197, 'LinkedIn': '', 'Nome': 'Patrícia Fumagalli', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'FSC GROUP', 'ID': 198, 'LinkedIn': '', 'Nome': 'Fernando Camargo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados & Análise', 'Descricao': '', 'Empresa': 'GAV RESORTS', 'ID': 199, 'LinkedIn': '', 'Nome': 'Renato Tomikawa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gestor de Dados e Análise', 'Descricao': '', 'Empresa': 'GAV RESORTS', 'ID': 200, 'LinkedIn': '', 'Nome': 'Robson da Silva Souza Junior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Especialista em Engenharia', 'Descricao': '', 'Empresa': 'GBMX', 'ID': 201, 'LinkedIn': '', 'Nome': 'Marcos Corazza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Governança de Dados', 'Descricao': '', 'Empresa': 'Getnet Adquirencia e Servicos', 'ID': 202, 'LinkedIn': '', 'Nome': 'Franco Ramires Reyes dos Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CDO/Head Data & Al', 'Descricao': '', 'Empresa': 'GETNET S.A..', 'ID': 203, 'LinkedIn': '', 'Nome': 'Rodrigo Caldoncelli Carvalho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Latam VP', 'Descricao': '', 'Empresa': 'Glean', 'ID': 204, 'LinkedIn': '', 'Nome': 'Leandro Lima', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Dados & IA', 'Descricao': '', 'Empresa': 'Globo', 'ID': 205, 'LinkedIn': '', 'Nome': 'Bianca Firmino', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Governança de dados', 'Descricao': '', 'Empresa': 'Globo', 'ID': 206, 'LinkedIn': '', 'Nome': 'Leonardo Blunk', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e IA', 'Descricao': '', 'Empresa': 'Globo', 'ID': 207, 'LinkedIn': '', 'Nome': 'Marina do Carmo Fernandes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Sr. de Dados e IA', 'Descricao': '', 'Empresa': 'Globo', 'ID': 208, 'LinkedIn': '', 'Nome': 'Thiago Madeira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CEO', 'Descricao': '', 'Empresa': 'GM Executive Voice', 'ID': 209, 'LinkedIn': '', 'Nome': 'Gabriel Moraes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Consultora', 'Descricao': '', 'Empresa': 'Governantes', 'ID': 210, 'LinkedIn': '', 'Nome': 'Tereza Cristina da Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'GRANADO', 'ID': 211, 'LinkedIn': '', 'Nome': 'Haroldo Proença', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de TI SR', 'Descricao': '', 'Empresa': 'Grupo Amil', 'ID': 212, 'LinkedIn': '', 'Nome': 'Carlos Bonilha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Engineer Leader', 'Descricao': '', 'Empresa': 'Grupo Boticário', 'ID': 213, 'LinkedIn': '', 'Nome': 'Anderson Cassoli', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de Produto de Dados e IA', 'Descricao': '', 'Empresa': 'Grupo Boticário', 'ID': 214, 'LinkedIn': '', 'Nome': 'Thiago Neubauer', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Manager', 'Descricao': '', 'Empresa': 'Grupo Boticário', 'ID': 215, 'LinkedIn': '', 'Nome': 'Vinicius Esteter', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Of Data', 'Descricao': '', 'Empresa': 'Grupo Direcional', 'ID': 216, 'LinkedIn': '', 'Nome': 'Marcos Paulo Rodrigues', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'COORDENADOR DE DADOS', 'Descricao': '', 'Empresa': 'GRUPO DPSP', 'ID': 217, 'LinkedIn': '', 'Nome': 'JOSE BALDESSIN', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Executivo de TI', 'Descricao': '', 'Empresa': 'Grupo DPSP', 'ID': 218, 'LinkedIn': '', 'Nome': 'William Mendonça', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'Grupo EP', 'ID': 219, 'LinkedIn': '', 'Nome': 'LUIS PAULO ANDRADE', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Al & Data Science Lead', 'Descricao': '', 'Empresa': 'Grupo Fleury', 'ID': 220, 'LinkedIn': '', 'Nome': 'Ana Carolina Prado Ricciardi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'ESPECIALISTA DE DADOS', 'Descricao': '', 'Empresa': 'GRUPO GPS', 'ID': 221, 'LinkedIn': '', 'Nome': 'LUCAS GOMES ATTUY', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CHRO', 'Descricao': '', 'Empresa': "Grupo Habib's", 'ID': 222, 'LinkedIn': '', 'Nome': 'Giba Godoy', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de Produtos de IA', 'Descricao': '', 'Empresa': 'Grupo Iter', 'ID': 223, 'LinkedIn': '', 'Nome': 'Luma dos Santos Corrêa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de T.I', 'Descricao': '', 'Empresa': 'Grupo Leonora', 'ID': 224, 'LinkedIn': '', 'Nome': 'José Kretzer', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Kora Saude', 'ID': 225, 'LinkedIn': '', 'Nome': 'Renata Vilanova Sampaio Mimessi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CFO', 'Descricao': '', 'Empresa': 'Laboratorios Bbraun', 'ID': 226, 'LinkedIn': '', 'Nome': 'Mariana Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Tecnologia', 'Descricao': '', 'Empresa': 'Latam Airlines', 'ID': 227, 'LinkedIn': '', 'Nome': 'Eduardo Kerchner', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados & IA', 'Descricao': '', 'Empresa': 'Leroin Merlin', 'ID': 228, 'LinkedIn': '', 'Nome': 'Leandro Galvão', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de dados & la', 'Descricao': '', 'Empresa': 'Leroy Merlin', 'ID': 229, 'LinkedIn': '', 'Nome': 'Paulo Shindi Kuniyoshi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'LEVE SAUDE', 'ID': 230, 'LinkedIn': '', 'Nome': 'Ailton Sampaio Junior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Engenheiro de Dados Sr.', 'Descricao': '', 'Empresa': 'LEVE SAUDE', 'ID': 231, 'LinkedIn': '', 'Nome': 'João Gabriel Neiva Guedes da Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora CX', 'Descricao': '', 'Empresa': 'Leve Saúde', 'ID': 232, 'LinkedIn': '', 'Nome': 'Raphaella Moratelli', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Acquisition Manager', 'Descricao': '', 'Empresa': 'LexisNexis', 'ID': 233, 'LinkedIn': '', 'Nome': 'Adriana Santos Lemos Machado', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Acquisição de Dados', 'Descricao': '', 'Empresa': 'LEXISNEXIS RISK SOLUTIONS', 'ID': 234, 'LinkedIn': '', 'Nome': 'Celso Rodrigues Pinto', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coord de Arq e GD', 'Descricao': '', 'Empresa': 'Libbs', 'ID': 235, 'LinkedIn': '', 'Nome': 'Aline Cyllio Rios Alvim', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'ANALISTA ATIVAÇÃO PROMOCIONAL', 'Descricao': '', 'Empresa': 'LIVELO', 'ID': 236, 'LinkedIn': '', 'Nome': 'LUISLA MADRUGA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Loft', 'ID': 237, 'LinkedIn': '', 'Nome': 'João Henrique Sena Ribeiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Estratégia de Al', 'Descricao': '', 'Empresa': 'LOJAS RIACHUELO', 'ID': 238, 'LinkedIn': '', 'Nome': 'Ana Lindiner Lima de Araujo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Arquiteto de Soluções', 'Descricao': '', 'Empresa': 'LOJAS RIACHUELO', 'ID': 239, 'LinkedIn': '', 'Nome': 'Daniel Capiton Vitor', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e Analytics', 'Descricao': '', 'Empresa': 'LOJAS TORRA', 'ID': 240, 'LinkedIn': '', 'Nome': 'André Soares', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de TI LAM', 'Descricao': '', 'Empresa': 'LSG Sky Chefs', 'ID': 241, 'LinkedIn': '', 'Nome': 'Willian Petrucelli', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Arquitetura', 'Descricao': '', 'Empresa': 'Luiz Moraes', 'ID': 242, 'LinkedIn': '', 'Nome': 'Luiz Fernando Freitas Moraes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CTO', 'Descricao': '', 'Empresa': 'Lumiar Healthcare', 'ID': 243, 'LinkedIn': '', 'Nome': 'CARLOS CESAR ROSA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Dados e IA', 'Descricao': '', 'Empresa': 'M2 Escola de Negócios', 'ID': 244, 'LinkedIn': '', 'Nome': 'Michel Pereira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of data strategy', 'Descricao': '', 'Empresa': 'Mag seguros', 'ID': 245, 'LinkedIn': '', 'Nome': 'Eduardo Gonçalves Branco de souza', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head do Centro de Controle', 'Descricao': '', 'Empresa': 'MAG SEGUROS', 'ID': 246, 'LinkedIn': '', 'Nome': 'Lúcio Rodrigues Duque Borges', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Lead Data & Analytics', 'Descricao': '', 'Empresa': 'MaisTODOS S.A.', 'ID': 247, 'LinkedIn': '', 'Nome': 'MARCIO FERREIRA JUNIOR', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Infra Digital', 'Descricao': '', 'Empresa': 'MARSH', 'ID': 248, 'LinkedIn': '', 'Nome': 'Fernando Momensso', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Technical Account', 'Descricao': '', 'Empresa': 'Mave & Velasco Consulting Ltda', 'ID': 249, 'LinkedIn': '', 'Nome': 'Martha Blanco Velasco', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Comercial Corporate', 'Descricao': '', 'Empresa': 'MAXXI INFORMATICA', 'ID': 250, 'LinkedIn': '', 'Nome': 'Karen Araujo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Global de CRM e Dados', 'Descricao': '', 'Empresa': 'MBRF S.A', 'ID': 251, 'LinkedIn': '', 'Nome': 'Sandro Copolla', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Transformation Business Partne', 'Descricao': '', 'Empresa': 'MEDLEY FARMACEUTICA LTDA.', 'ID': 252, 'LinkedIn': '', 'Nome': 'Carolina Cancela', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de TI', 'Descricao': '', 'Empresa': 'MENTORE', 'ID': 253, 'LinkedIn': '', 'Nome': 'Lucio Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Engenharia', 'Descricao': '', 'Empresa': 'MERCADO LIVRE', 'ID': 254, 'LinkedIn': '', 'Nome': 'Thiago Antonio Amicussi Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Ger. Log & Inteligência Dados', 'Descricao': '', 'Empresa': 'Mercedes-Benz do Brasil', 'ID': 255, 'LinkedIn': '', 'Nome': 'Bruno Fuzetti', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de TI - Data%IA', 'Descricao': '', 'Empresa': 'Metrô', 'ID': 256, 'LinkedIn': '', 'Nome': 'Adilson de Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'METRO SP', 'ID': 257, 'LinkedIn': '', 'Nome': 'ALEXANDRE MAURI', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista', 'Descricao': '', 'Empresa': 'Metrô SP', 'ID': 258, 'LinkedIn': '', 'Nome': 'Natália Salmazzo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista', 'Descricao': '', 'Empresa': 'Metrô SP', 'ID': 259, 'LinkedIn': '', 'Nome': 'Oseias Gomes Pereira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Engenharia de Dados', 'Descricao': '', 'Empresa': 'Michelin Connected Fleet', 'ID': 260, 'LinkedIn': '', 'Nome': 'Achiles Bianchi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e IA', 'Descricao': '', 'Empresa': 'Michelin Connected Fleet', 'ID': 261, 'LinkedIn': '', 'Nome': 'Caio Barcala', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de dados IA e arquitet', 'Descricao': '', 'Empresa': 'Obramax', 'ID': 262, 'LinkedIn': '', 'Nome': 'André Agostinho', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'SAP Tech Lead', 'Descricao': '', 'Empresa': 'Obramax', 'ID': 263, 'LinkedIn': '', 'Nome': 'Caio Campos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e Governança', 'Descricao': '', 'Empresa': 'Opella', 'ID': 264, 'LinkedIn': '', 'Nome': 'Guilherme Polim', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Técnico', 'Descricao': '', 'Empresa': 'Ourofino', 'ID': 265, 'LinkedIn': '', 'Nome': 'Junior Nogueira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Exec. de Dados e IA', 'Descricao': '', 'Empresa': 'Ourofino', 'ID': 266, 'LinkedIn': '', 'Nome': 'Lucas Polin', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CPTO', 'Descricao': '', 'Empresa': 'Ourofino', 'ID': 267, 'LinkedIn': '', 'Nome': 'Matheus Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'Ourofino', 'ID': 268, 'LinkedIn': '', 'Nome': 'Matheus Marmol', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Lead IA', 'Descricao': '', 'Empresa': 'PAC', 'ID': 269, 'LinkedIn': '', 'Nome': 'Rosane Chene', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Lead Analytics', 'Descricao': '', 'Empresa': 'PAC', 'ID': 270, 'LinkedIn': '', 'Nome': 'Joyce Goes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Arquiteto de dados', 'Descricao': '', 'Empresa': 'PAC', 'ID': 271, 'LinkedIn': '', 'Nome': 'Maria Leite', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Lead Engenharia', 'Descricao': '', 'Empresa': 'PAC', 'ID': 272, 'LinkedIn': '', 'Nome': 'Eduardo Camargo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Relacionamento PF', 'Descricao': '', 'Empresa': 'Pacaembu', 'ID': 273, 'LinkedIn': '', 'Nome': 'Fernando Henrique Weigel', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretora', 'Descricao': '', 'Empresa': 'Pacaembu Autopeças', 'ID': 274, 'LinkedIn': '', 'Nome': 'Rodrigo Morokuma', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gestora Marketing/Voluntariado', 'Descricao': '', 'Empresa': 'PANVEL FARMACIAS', 'ID': 275, 'LinkedIn': '', 'Nome': 'Geovani Balestrin Scalconb', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Relacionamento', 'Descricao': '', 'Empresa': 'PANVEL FARMACIAS', 'ID': 276, 'LinkedIn': '', 'Nome': 'FILIPE MOLINA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor TI', 'Descricao': '', 'Empresa': 'PEPSICO', 'ID': 277, 'LinkedIn': '', 'Nome': 'Bruno Iglesias Borges Rodrigues', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Inteligência e Dados', 'Descricao': '', 'Empresa': 'PETROBRAS', 'ID': 278, 'LinkedIn': '', 'Nome': 'Rodrigo José Panza Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados & IA', 'Descricao': '', 'Empresa': 'PETROBRAS', 'ID': 279, 'LinkedIn': '', 'Nome': 'Aislan Ribeiro Greca', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Executivo IA e Dados', 'Descricao': '', 'Empresa': 'PETROBRAS - EDISE', 'ID': 280, 'LinkedIn': '', 'Nome': 'Gederson Lourencon', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'GERENTE SR', 'Descricao': '', 'Empresa': 'PICPAY', 'ID': 281, 'LinkedIn': '', 'Nome': 'Gustavo Tadao Okida', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Setorial', 'Descricao': '', 'Empresa': 'PicPay', 'ID': 282, 'LinkedIn': '', 'Nome': 'Pedro Lage', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de Analytics e IA SMS', 'Descricao': '', 'Empresa': 'Pintores com a Boca e os Pés', 'ID': 283, 'LinkedIn': '', 'Nome': 'Karina Seraggi Contini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Cientista de Dados', 'Descricao': '', 'Empresa': 'Portal Telemedicina', 'ID': 284, 'LinkedIn': '', 'Nome': 'Bruno Baldini', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de engenharia de dados', 'Descricao': '', 'Empresa': 'PORTO', 'ID': 285, 'LinkedIn': '', 'Nome': 'FERNANDO MARTINS', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Executivo de Dados', 'Descricao': '', 'Empresa': 'Porto', 'ID': 286, 'LinkedIn': '', 'Nome': 'Kayo Correa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados', 'Descricao': '', 'Empresa': 'Porto', 'ID': 287, 'LinkedIn': '', 'Nome': 'Priscilla Campos Ferraz', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Operacional', 'Descricao': '', 'Empresa': 'Porto Bank', 'ID': 288, 'LinkedIn': '', 'Nome': 'Gustavo Lessa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Technologia', 'Descricao': '', 'Empresa': 'Porto Bank', 'ID': 289, 'LinkedIn': '', 'Nome': 'LEONARDO MARINI', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Analytics & Al', 'Descricao': '', 'Empresa': 'PORTO BANK', 'ID': 290, 'LinkedIn': '', 'Nome': 'Marcelo da Quinta Oses', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder de Governança de Dados', 'Descricao': '', 'Empresa': 'Porto Bank', 'ID': 291, 'LinkedIn': '', 'Nome': 'Wilian Germano', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of growth analytics', 'Descricao': '', 'Empresa': 'Porto Seguro', 'ID': 292, 'LinkedIn': '', 'Nome': 'Edson Lopes de Sousa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Group Product', 'Descricao': '', 'Empresa': 'PORTONAVE', 'ID': 293, 'LinkedIn': '', 'Nome': 'PETERSON DA ROSA SILVA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de dados', 'Descricao': '', 'Empresa': 'Pravaler', 'ID': 294, 'LinkedIn': '', 'Nome': 'Gabriella Caracciolo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Media Analytics', 'Descricao': '', 'Empresa': 'PROCTER & GAMBLE', 'ID': 295, 'LinkedIn': '', 'Nome': 'Vinicius Fugulin Barbosa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Growth', 'Descricao': '', 'Empresa': 'PROFECTUM TECNOLOGIA', 'ID': 296, 'LinkedIn': '', 'Nome': 'Rômulo Felipe Guedes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'PROFIRO MATERIAIS PARA CONSTRUCAO', 'ID': 297, 'LinkedIn': '', 'Nome': 'Weslley da Savana', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador BI LATAM', 'Descricao': '', 'Empresa': 'Prysmian', 'ID': 298, 'LinkedIn': '', 'Nome': 'Lucas Mota', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Digital Manager', 'Descricao': '', 'Empresa': 'Prysmian', 'ID': 299, 'LinkedIn': '', 'Nome': 'Diego Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Al', 'Descricao': '', 'Empresa': 'PwC', 'ID': 300, 'LinkedIn': '', 'Nome': 'Marcos Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Governança de Dados', 'Descricao': '', 'Empresa': 'PwC', 'ID': 301, 'LinkedIn': '', 'Nome': 'Barbara Carlos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Chief Data Officer', 'Descricao': '', 'Empresa': 'PwC', 'ID': 302, 'LinkedIn': '', 'Nome': 'Miguel Barreira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Soluções e Projetos', 'Descricao': '', 'Empresa': 'PwC', 'ID': 303, 'LinkedIn': '', 'Nome': 'Emerson Martins', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'QSOFT-SP', 'ID': 304, 'LinkedIn': '', 'Nome': 'Marcelo Gomes da Cruz', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coord Data Analitycs e IA', 'Descricao': '', 'Empresa': 'RD Saude', 'ID': 305, 'LinkedIn': '', 'Nome': 'Dernier Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Tech Lead', 'Descricao': '', 'Empresa': 'RD Saude', 'ID': 306, 'LinkedIn': '', 'Nome': 'Felippe Scotti', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Executivo Data & IA', 'Descricao': '', 'Empresa': 'RD SAUDE', 'ID': 307, 'LinkedIn': '', 'Nome': 'Leonardo Nascimento', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de CoE de IA', 'Descricao': '', 'Empresa': 'RD Saude', 'ID': 308, 'LinkedIn': '', 'Nome': 'Vanessa Guber', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coord data analitycs e IA', 'Descricao': '', 'Empresa': 'RD saúde', 'ID': 309, 'LinkedIn': '', 'Nome': 'Dernier silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Financial Data & Al', 'Descricao': '', 'Empresa': 'RD STATION', 'ID': 310, 'LinkedIn': '', 'Nome': 'Gabriel Tiengo Pontes', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Dados & Al', 'Descricao': '', 'Empresa': 'Reclame Aqui', 'ID': 311, 'LinkedIn': '', 'Nome': 'Ricardo Faria', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'VP Tecnologia', 'Descricao': '', 'Empresa': 'Rede Americas', 'ID': 312, 'LinkedIn': '', 'Nome': 'Felipe Starling', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de sistemas Digitais', 'Descricao': '', 'Empresa': 'Rede Americas', 'ID': 313, 'LinkedIn': '', 'Nome': 'MARIA A. DANNA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CTO', 'Descricao': '', 'Empresa': 'Rede ANCORA', 'ID': 314, 'LinkedIn': '', 'Nome': 'Daniel Destro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'REDE MADRE', 'ID': 315, 'LinkedIn': '', 'Nome': 'Paulo Ferreira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados & IA', 'Descricao': '', 'Empresa': 'RENAPSI', 'ID': 316, 'LinkedIn': '', 'Nome': 'BARBARA FERREIRA BEZERRA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CEO & Founder', 'Descricao': '', 'Empresa': 'Resolva Ai', 'ID': 317, 'LinkedIn': '', 'Nome': 'vicente dalvo camillo neto', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Sistemas', 'Descricao': '', 'Empresa': 'Riachuelo', 'ID': 318, 'LinkedIn': '', 'Nome': 'Alexandre Boaventura', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor TI', 'Descricao': '', 'Empresa': 'RIACHUELO', 'ID': 319, 'LinkedIn': '', 'Nome': 'Gustavo Pereira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Tecnologia', 'Descricao': '', 'Empresa': 'Riachuelo', 'ID': 320, 'LinkedIn': '', 'Nome': 'WELLINGTON JOSE DA SILVA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Analista de Dados', 'Descricao': '', 'Empresa': 'RIOSULENSE', 'ID': 321, 'LinkedIn': '', 'Nome': 'Mohammad Basciri Nimer Hammad', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Eng/Arch Lead', 'Descricao': '', 'Empresa': 'Roche Farma', 'ID': 322, 'LinkedIn': '', 'Nome': 'Sérgio Paro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de TI', 'Descricao': '', 'Empresa': 'RODOBENS', 'ID': 323, 'LinkedIn': '', 'Nome': 'Daniela Maria de Souza Alves', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de TI', 'Descricao': '', 'Empresa': 'Rodobens', 'ID': 324, 'LinkedIn': '', 'Nome': 'LEONARDO BATISTA P DOS SANTOS FAJARDO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Superintendente de TI', 'Descricao': '', 'Empresa': 'Rodobens $S/A$', 'ID': 325, 'LinkedIn': '', 'Nome': 'Daniela Monteiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Eng. e Gov. de Dado', 'Descricao': '', 'Empresa': 'Rumo', 'ID': 326, 'LinkedIn': '', 'Nome': 'Luana Javoni', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coord. Gov. Dados', 'Descricao': '', 'Empresa': 'Rumo Logistica', 'ID': 327, 'LinkedIn': '', 'Nome': 'Getulio Oliveira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Insights Manager', 'Descricao': '', 'Empresa': 'RX Global', 'ID': 328, 'LinkedIn': '', 'Nome': 'Rebeca Moratta Dalonço', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de IA, Dados e Analytics', 'Descricao': '', 'Empresa': 'SABESP', 'ID': 329, 'LinkedIn': '', 'Nome': 'Eric Vinicius de Carvalho Leite', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Analytics Leader', 'Descricao': '', 'Empresa': 'SABESP', 'ID': 330, 'LinkedIn': '', 'Nome': 'Ernesto Kuruma', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Produtos Ti', 'Descricao': '', 'Empresa': 'Usiminas', 'ID': 331, 'LinkedIn': '', 'Nome': 'Piter Sampaio', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'INFORMATION TECHNOLOGY ANALYST', 'Descricao': '', 'Empresa': 'Usiminas', 'ID': 332, 'LinkedIn': '', 'Nome': 'WATSON RODRIGO SILVA SOARES', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Operações', 'Descricao': '', 'Empresa': 'V.TAL', 'ID': 333, 'LinkedIn': '', 'Nome': 'Ewerson Silva', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenadora de D', 'Descricao': '', 'Empresa': 'Valgroup', 'ID': 334, 'LinkedIn': '', 'Nome': 'Francine Barbosa', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Líder Gestão de Demandas', 'Descricao': '', 'Empresa': 'VALGROUP', 'ID': 335, 'LinkedIn': '', 'Nome': 'Marilúcia Carvalho de O. Ribeiro', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Corporativo de TI', 'Descricao': '', 'Empresa': 'Valgroup', 'ID': 336, 'LinkedIn': '', 'Nome': 'TARCISIO CARVALHO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'diretor infra e seginfo', 'Descricao': '', 'Empresa': 'valloo', 'ID': 337, 'LinkedIn': '', 'Nome': 'luiz watanabe', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'Vedacit', 'ID': 338, 'LinkedIn': '', 'Nome': 'Carlos Violante', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO', 'Descricao': '', 'Empresa': 'VEOLIA', 'ID': 339, 'LinkedIn': '', 'Nome': 'Adriana Moreira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'DIRETOR', 'Descricao': '', 'Empresa': 'VIBRA ENERGIA', 'ID': 340, 'LinkedIn': '', 'Nome': 'RENATO CORREA VIEIRA', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Sr DTC Manager', 'Descricao': '', 'Empresa': 'Visa', 'ID': 341, 'LinkedIn': '', 'Nome': 'Erica Florencio', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Dados & IA', 'Descricao': '', 'Empresa': 'VISA', 'ID': 342, 'LinkedIn': '', 'Nome': 'Valter Junior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de DevEx e IA Adoption', 'Descricao': '', 'Empresa': 'Vivo', 'ID': 343, 'LinkedIn': '', 'Nome': 'Jonathan Santos', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Arquitetura', 'Descricao': '', 'Empresa': 'VOKE', 'ID': 344, 'LinkedIn': '', 'Nome': 'Flávio Jirus Nhoncance', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente Executivo', 'Descricao': '', 'Empresa': 'Volkswagen do Brasil', 'ID': 345, 'LinkedIn': '', 'Nome': 'Fernando de Andrade', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Coordenador de Dados', 'Descricao': '', 'Empresa': 'Votorantim Cimentos', 'ID': 346, 'LinkedIn': '', 'Nome': 'Leonardo Baumeister', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Governance', 'Descricao': '', 'Empresa': 'Votorantim Cimentos', 'ID': 347, 'LinkedIn': '', 'Nome': 'Thiago Strobilius', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor Dados e IA', 'Descricao': '', 'Empresa': 'VR', 'ID': 348, 'LinkedIn': '', 'Nome': 'Gustavo do Prado Barros Gerolamo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Manager', 'Descricao': '', 'Empresa': 'VR', 'ID': 349, 'LinkedIn': '', 'Nome': 'Luiz Zerbinatti', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Dados e IA', 'Descricao': '', 'Empresa': 'WAP', 'ID': 350, 'LinkedIn': '', 'Nome': 'Beatriz Paulino', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'HEAD DATΑ & ΑΙ', 'Descricao': '', 'Empresa': 'WHIRLPOOL CORP', 'ID': 351, 'LinkedIn': '', 'Nome': 'Robson Mendonça', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor de Dados', 'Descricao': '', 'Empresa': 'Woba', 'ID': 352, 'LinkedIn': '', 'Nome': 'José Nilson dos Santos Júnior', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Strategy Manager', 'Descricao': '', 'Empresa': 'Woba', 'ID': 353, 'LinkedIn': '', 'Nome': 'Juliana Pereira Veloso', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CAIO & Founder', 'Descricao': '', 'Empresa': 'Woman in Tech', 'ID': 354, 'LinkedIn': '', 'Nome': 'Lucia de Fátima Souza de Almeida', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head of Data & Analytics', 'Descricao': '', 'Empresa': 'Yara', 'ID': 355, 'LinkedIn': '', 'Nome': 'Marcus Teixeira', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data Manager', 'Descricao': '', 'Empresa': 'YDUQS', 'ID': 356, 'LinkedIn': '', 'Nome': 'BRUNO ALMEIDA DOS SANTOS', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head Digital Technology', 'Descricao': '', 'Empresa': 'YDUOS S.A.', 'ID': 357, 'LinkedIn': '', 'Nome': 'Bruno Rocha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Superintendente de TI', 'Descricao': '', 'Empresa': 'Zurich Brasil', 'ID': 358, 'LinkedIn': '', 'Nome': 'Ricardo Shigueaki Nozuma', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Diretor', 'Descricao': '', 'Empresa': 'EPTV', 'ID': 359, 'LinkedIn': '', 'Nome': 'Luis Paulo', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CEO Founder', 'Descricao': '', 'Empresa': 'QUIPE AI CURVAC ECOSSISTEMAS', 'ID': 360, 'LinkedIn': '', 'Nome': 'Luiz Guilherme', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente', 'Descricao': '', 'Empresa': 'Odontoprev', 'ID': 361, 'LinkedIn': '', 'Nome': 'Thiago Takahashi', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados IA', 'Descricao': '', 'Empresa': 'Stone', 'ID': 362, 'LinkedIn': '', 'Nome': 'Bruno Tomazela', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Head de Dados', 'Descricao': '', 'Empresa': 'StoneCo', 'ID': 363, 'LinkedIn': '', 'Nome': 'Bruno Tomazela', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente de Produto de Dados', 'Descricao': '', 'Empresa': 'DATAPREV', 'ID': 364, 'LinkedIn': '', 'Nome': 'SAVIO NASCIMENTO', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'CIO / Diretora de TI', 'Descricao': '', 'Empresa': 'MCIO', 'ID': 365, 'LinkedIn': '', 'Nome': 'Sylvia C. Sanchez', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Data & Al Leader', 'Descricao': '', 'Empresa': 'Paramount Têxteis', 'ID': 366, 'LinkedIn': '', 'Nome': 'Deives Nepomuceno', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''},
    {'Cargo': 'Gerente', 'Descricao': '', 'Empresa': 'DATAPREV', 'ID': 367, 'LinkedIn': '', 'Nome': 'Dayse Rocha', 'Podcast': False, 'Prioritario': False, 'Status': 'whatsapp não enviado', 'Tema': ''}
]

# Função de Envio em Lote (Bulk Insert)
def sync_initial_leads_to_db():
    try:
        supabase.table("leads").delete().gt("id", 0).execute()
        
        lote = []
        for l in INITIAL_LEADS:
            lote.append({
                "id": l["ID"],
                "nome": l["Nome"],
                "empresa": l["Empresa"],
                "cargo": l["Cargo"],
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
                        "Podcast": False,
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
        podcast_html = '<span class="podcast-tag">🎙️ Podcast</span>' if l.get("Podcast") else ""
        status_html = f"<span class='status-tag'>{l.get('Status', 'whatsapp não enviado')}</span>"
        
        card = f"""
        <div class="lead-row">
            <div style="display:flex; align-items:center; gap:15px;">
                {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "small")}
                <div style="flex:1;">
                    <strong style="font-size: 1.1rem;">{l['Nome']}</strong> {status_html} {star_html} {podcast_html}<br>
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
            
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

elif st.session_state.view_mode == 'detail':
    l = next(item for item in st.session_state.leads_list if item['ID'] == st.session_state.selected_lead_id)
    lead_ref = get_lead_ref(l)
    
    if st.button("← Voltar"): 
        st.session_state.view_mode = 'list'
        st.rerun()
        
    star_badge = '<span class="star-tag">⭐ Prioritário</span>' if l.get("Prioritario") else ""
    podcast_badge = '<span class="podcast-tag">🎙️ Podcast</span>' if l.get("Podcast") else ""
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px; margin: 20px 0;">
        {get_photo_html(l['Nome'], l.get('LinkedIn', '#'), "large")}
        <div>
            <h1 style="margin:0;">{l['Nome']} {star_badge} {podcast_badge}</h1>
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
