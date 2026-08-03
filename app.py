<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Controle de Leads & Operação GT</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen">

    <!-- Header & Perfil do Usuário -->
    <header class="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <i class="fa-solid fa-users-gear text-blue-500 text-2xl"></i>
                <h1 class="text-xl font-bold tracking-wide">Gestão de Leads GT</h1>
            </div>

            <!-- Usuário logado no sistema: Spinelli -->
            <div class="flex items-center space-x-4">
                <div class="text-right">
                    <p class="text-sm font-semibold text-slate-200" id="user-display-name">Spinelli</p>
                    <p class="text-xs text-blue-400">Gestor / Administrador</p>
                </div>
                <div class="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold border-2 border-blue-400">
                    S
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8 space-y-8">
        
        <!-- Ações Globais -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-800 p-6 rounded-xl border border-slate-700 gap-4">
            <div>
                <h2 class="text-lg font-semibold text-white">Painel Operacional</h2>
                <p class="text-sm text-slate-400">Gerenciamento de entrevistados, roteiros e logs do sistema.</p>
            </div>
            
            <div class="flex flex-wrap gap-3">
                <button onclick="openAddLeadModal()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2">
                    <i class="fa-solid fa-plus"></i> Novo Lead
                </button>
                <button onclick="requestClearLogs()" class="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2">
                    <i class="fa-solid fa-trash-can"></i> Apagar Logs
                </button>
            </div>
        </div>

        <!-- Tabela de Leads -->
        <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
            <div class="p-6 border-b border-slate-700">
                <h3 class="text-md font-semibold text-white">Leads Cadastrados (<span id="lead-count">0</span>)</h3>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-900/50 text-slate-400 uppercase text-xs">
                        <tr>
                            <th class="px-6 py-4">Chave de Perfil</th>
                            <th class="px-6 py-4">Nome</th>
                            <th class="px-6 py-4">Empresa / Cargo</th>
                            <th class="px-6 py-4">Contato</th>
                            <th class="px-6 py-4">Entrevista</th>
                            <th class="px-6 py-4 text-center text-nowrap">Ações / Status</th>
                        </tr>
                    </thead>
                    <tbody id="leads-table-body" class="divide-y divide-slate-700">
                        <!-- Renderizado via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Histórico de Logs -->
        <div class="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <h3 class="text-md font-semibold text-white mb-4 flex items-center gap-2">
                <i class="fa-solid fa-list-check text-slate-400"></i> Histórico de Logs do Sistema
            </h3>
            <div id="logs-container" class="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-400 h-40 overflow-y-auto space-y-1 border border-slate-800">
                <!-- Logs adicionados via JS -->
            </div>
        </div>

    </main>

    <!-- MODAL: Confirmação para Apagar Logs -->
    <div id="confirm-delete-modal" class="fixed inset-0 bg-black/70 flex items-center justify-center hidden z-50">
        <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 max-w-md w-full mx-4 space-y-4 shadow-2xl">
            <div class="flex items-center space-x-3 text-red-500">
                <i class="fa-solid fa-triangle-exclamation text-2xl"></i>
                <h4 class="text-lg font-bold text-white">Confirmar Exclusão</h4>
            </div>
            <p class="text-sm text-slate-300">Tem certeza que deseja apagar os logs do sistema? Esta ação é irreversível.</p>
            <div class="flex justify-end space-x-3 pt-2">
                <button onclick="closeModal('confirm-delete-modal')" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm transition">Cancelar</button>
                <button onclick="confirmClearLogs()" class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition">Sim, Apagar Logs</button>
            </div>
        </div>
    </div>

    <!-- MODAL: Adicionar Novo Lead -->
    <div id="lead-modal" class="fixed inset-0 bg-black/70 flex items-center justify-center hidden z-50 overflow-y-auto py-10">
        <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 max-w-xl w-full mx-4 space-y-4 shadow-2xl">
            <h4 class="text-lg font-bold text-white">Adicionar Novo Lead</h4>
            <form id="lead-form" onsubmit="saveLead(event)" class="space-y-3">
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Nome do Entrevistado *</label>
                    <input type="text" id="input-name" required class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-xs font-semibold text-slate-400 mb-1">Empresa</label><input type="text" id="input-company" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                    <div><label class="block text-xs font-semibold text-slate-400 mb-1">Cargo</label><input type="text" id="input-role" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div><label class="block text-xs font-semibold text-slate-400 mb-1">E-mail</label><input type="email" id="input-email" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                    <div><label class="block text-xs font-semibold text-slate-400 mb-1">WhatsApp</label><input type="text" id="input-whatsapp" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                </div>
                <div><label class="block text-xs font-semibold text-slate-400 mb-1">Tema da Entrevista</label><input type="text" id="input-topic" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                <div><label class="block text-xs font-semibold text-slate-400 mb-1">Descrição / Detalhes</label><textarea id="input-desc" rows="3" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></textarea></div>
                <div><label class="block text-xs font-semibold text-slate-400 mb-1">LinkedIn (Deixe em branco p/ gerar ID automático)</label><input type="url" id="input-linkedin" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"></div>
                <div class="flex justify-end space-x-3 pt-3">
                    <button type="button" onclick="closeModal('lead-modal')" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm transition">Cancelar</button>
                    <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition">Salvar Lead</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Script Principal -->
    <script>
        // 1. Usuário do Sistema
        const currentSystemUser = { id: "user-spinelli", name: "Spinelli", role: "Gestor / Administrador" };

        // 2. Base de Leads EXATA (Somente os novos da planilha)
        const rawLeadsData = [
            {
                name: "Giuliane Paulista", role: "AI & Analytics Executive", company: "Banco do Brasil",
                whatsapp: "61 9381-9792", email: "Giuliane@bb.com.br", interviewDate: "2026-08-04", interviewTime: "17h",
                topic: "Construindo confiança na Era da IA: Jornada do Banco do Brasil em governança, capacitação e maturidade",
                description: "- Estratégias para construir governança de dados e IA em escala: como estruturar um modelo de governança sólido em uma instituição do porte do Banco do Brasil\n\n- Os caminhos para alfabetizar em dados e IA milhares de colaboradores com diferentes níveis de maturidade, transformando resistência em engajamento.\n\n- Quais métricas e marcos práticos ajudam a avaliar se a organização está evoluindo de forma madura, segura e alinhada às exigências regulatórias do setor financeiro.\n\n- Como o Banco do Brasil equilibra o entusiasmo com novos modelos de IA e a necessidade de garantir respostas confiáveis, transparentes e sem alucinações.",
                linkedin: "https://www.linkedin.com/in/giulianepaulista/", status: "whatsapp não enviado"
            },
            {
                name: "Sara Sitta e Fernanda Vargas", role: "AI & Data Science Lead (Sara)", company: "Ford",
                whatsapp: "11 98331-0188", email: "ssitta@ford.com", interviewDate: "2026-08-06", interviewTime: "15h",
                topic: "Fast Cases — Dados, IA, pessoas e ROI em empresas brasileiras",
                description: "- Como identificar rapidamente oportunidades de Dados e IA na indústria que tenham ciclo curto de implementação e forte potencial de retorno financeiro.\n\n- Quais são os principais gargalos ao mover projetos da fase de testes para a operação diária e como garantir que o ROI seja refletido no balanço financeiro.\n\n- Como definir KPIs claros e atribuir valor financeiro a iniciativas de Inteligência Artificial (de modelos tradicionais a GenAI)\n\n- Como construir uma base de dados sólida e pipelines resilientes.",
                linkedin: "https://www.linkedin.com/in/sarasitta/", status: "whatsapp não enviado"
            },
            {
                name: "Gabriel Vernalha Ribeiro", role: "Executivo de Dados, Analytics e IA", company: "Dasa",
                whatsapp: "11 99313-7047", email: "gabriel.vernalha@dasa.com.br", interviewDate: "2026-08-04", interviewTime: "15h",
                topic: "Liderando o Futuro / Board Reverse Pitch: A IA muda tudo?",
                description: "- Como liderar a agenda de implementação da IA em um ecossistema tão crítico e regulado quanto o de saúde.\n\n- Como conduzir a conversa com conselheiros e acionistas sem cair no exagero do hype, balanceando grandes promessas com retorno claro de investimento, gestão de riscos e segurança do paciente.\n\n- Estratégias práticas para manter a conformidade (LGPD/hipaa), a privacidade de dados médicos e a qualidade analítica sem travar a inovação.",
                linkedin: "https://www.linkedin.com/in/gvribeiro/", status: "whatsapp não enviado"
            },
            {
                name: "Gabriel Mochnacs", role: "Superintendente de Dados e IA", company: "Cielo",
                whatsapp: "11 99682-4822", email: "Mochnacs@cielo.com.br", interviewDate: "2026-08-04", interviewTime: "09h",
                topic: "O que ninguém conta sobre escalar IA: falhas, dados, governança e decisões de negócio",
                description: "- Quais são os principais motivos que fazem projetos promissores falharem e o que a dor da tentativa ensina sobre maturidade de dados.\n\n- Quais decisões técnicas, de governança e de arquitetura precisam ser tomadas no \"dia zero\" para garantir que uma prova de conceito consiga suportar o volume de um gigante de pagamentos como a Cielo.\n\n- A importância de construir capacidades sólidas de observabilidade e arquitetura em nuvem para sustentar modelos avançados de IA sem explodir custos operacionais.",
                linkedin: "https://www.linkedin.com/in/gabrielmarruda/", status: "whatsapp não enviado"
            },
            {
                name: "Gustavo Nery", role: "CIO", company: "Anatel",
                whatsapp: "61 8134-9289", email: "gustavo.nery@anatel.gov.br", interviewDate: "2026-08-04", interviewTime: "10h",
                topic: "O que ninguém conta sobre escalar IA",
                description: "- Os gargalos invisíveis e burocráticos de infraestrutura, dados e compras públicas que dificultam que soluções de IA saiam do papel e virem serviço público.\n\n- Como lidar com as falhas inerentes aos modelos de IA em um ambiente estatal onde a transparência e a responsabilidade legal são exigências absolutas perante órgãos de controle e a sociedade.\n\n- TransformaGov e a virada para a gestão pública orientada a dados: lições aprendidas em grandes programas de transformação do Estado.",
                linkedin: "https://www.linkedin.com/in/gustavo-nery-silva/", status: "whatsapp não enviado"
            },
            {
                name: "Sabrina Nazario", role: "CDO SAM", company: "Schneider Electric",
                whatsapp: "11 93433-1131", email: "Sabrina.nazario@se.com", interviewDate: "2026-08-05", interviewTime: "15h",
                topic: "Governança e Estratégia de Dados na América do Sul: Desafios e Escala Regional",
                description: "- Os desafios de desenhar e implementar uma estratégia de dados coesa para toda LATAM, considerando as particularidades locais e as diretrizes globais de uma empresa gigante como a Schneider Electric.\n\n- Como estruturar uma governança de dados eficiente que garanta qualidade, conformidade e segurança sem criar burocracia excessiva ou travar a agilidade e a inovação das equipes.\n\n- Quais estratégias e iniciativas práticas têm sido mais eficazes para vencer a resistência à mudança.",
                linkedin: "https://www.linkedin.com/in/sabrina-nazario-7138a822/", status: "whatsapp não enviado"
            }
        ];

        let leads = [];
        let systemLogs = [];

        // 3. Fallback de Chave (LinkedIn ou slug)
        function getLeadProfileKey(lead) {
            if (lead.linkedin && lead.linkedin.trim() !== "") return lead.linkedin.trim();
            const safeName = (lead.name || 'user').toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "-");
            const safeCompany = (lead.company || 'empresa').toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "-");
            return `key-${safeName}-${safeCompany}`;
        }

        // 4. Iniciar Sistema
        function initSystem() {
            leads = rawLeadsData.map(lead => ({ ...lead, profileKey: getLeadProfileKey(lead) }));
            addLog(`Sistema iniciado por ${currentSystemUser.name}.`);
            renderLeadsTable();
        }

        // 5. Toggle de Menu Oculto (Accordion)
        function toggleDetails(profileKey) {
            const tr = document.getElementById(`details-${profileKey}`);
            const icon = document.getElementById(`icon-${profileKey}`);
            if (tr.classList.contains('hidden')) {
                tr.classList.remove('hidden');
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            } else {
                tr.classList.add('hidden');
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            }
        }

        // 6. Atualizar Status do WhatsApp
        function updateStatus(profileKey, newStatus) {
            const lead = leads.find(l => l.profileKey === profileKey);
            if(lead) {
                const oldStatus = lead.status;
                lead.status = newStatus;
                addLog(`Status de '${lead.name}' alterado de "${oldStatus}" para "${newStatus}" por ${currentSystemUser.name}.`);
            }
        }

        // 7. Renderizar Tabela + Linhas Ocultas
        function renderLeadsTable() {
            const tbody = document.getElementById('leads-table-body');
            document.getElementById('lead-count').innerText = leads.length;

            if (leads.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-500">Nenhum lead cadastrado.</td></tr>`;
                return;
            }

            let html = '';
            leads.forEach(lead => {
                // Status do Select
                const selOp1 = lead.status === 'whatsapp não enviado' ? 'selected' : '';
                const selOp2 = lead.status === 'mensagem 01 enviada' ? 'selected' : '';
                const selOp3 = lead.status === 'lead respondeu' ? 'selected' : '';
                const selOp4 = lead.status === 'lead não respondeu' ? 'selected' : '';

                html += `
                <!-- Linha Principal -->
                <tr class="hover:bg-slate-700/50 transition border-b border-slate-700/50">
                    <td class="px-6 py-4 font-mono text-xs text-blue-400 break-all">
                        <span class="bg-slate-900 border border-slate-700 px-2 py-1 rounded inline-block max-w-[150px] truncate" title="${lead.profileKey}">
                            ${lead.profileKey}
                        </span>
                    </td>
                    <td class="px-6 py-4 font-medium text-white">${lead.name}</td>
                    <td class="px-6 py-4">
                        <div class="font-medium text-slate-200">${lead.company || '-'}</div>
                        <div class="text-xs text-slate-400">${lead.role || '-'}</div>
                    </td>
                    <td class="px-6 py-4 text-xs">
                        <div><i class="fa-solid fa-envelope text-slate-500 mr-1"></i> ${lead.email || '-'}</div>
                        <div><i class="fa-solid fa-phone text-slate-500 mr-1"></i> ${lead.whatsapp || '-'}</div>
                    </td>
                    <td class="px-6 py-4 text-xs">
                        <span class="bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">
                            ${lead.interviewDate || 'A definir'} ${lead.interviewTime ? 'às ' + lead.interviewTime : ''}
                        </span>
                    </td>
                    <td class="px-6 py-4 text-center text-nowrap">
                        <button onclick="toggleDetails('${lead.profileKey}')" class="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-lg text-xs mr-2 transition" title="Ver Detalhes e Status">
                            <i id="icon-${lead.profileKey}" class="fa-solid fa-chevron-down mr-1"></i> Expandir
                        </button>
                        ${lead.linkedin ? `
                            <a href="${lead.linkedin}" target="_blank" class="text-blue-400 hover:text-blue-300 mr-2" title="Abrir LinkedIn">
                                <i class="fa-brands fa-linkedin text-lg"></i>
                            </a>
                        ` : `
                            <span class="text-slate-600 mr-2" title="Sem LinkedIn"><i class="fa-solid fa-link-slash text-lg"></i></span>
                        `}
                        <button onclick="deleteLead('${lead.profileKey}')" class="text-red-400 hover:text-red-300" title="Excluir Lead">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
                <!-- Linha Oculta (Detalhes e Status) -->
                <tr id="details-${lead.profileKey}" class="hidden bg-slate-800/80 border-b border-slate-700 shadow-inner">
                    <td colspan="6" class="px-6 py-4">
                        <div class="flex flex-col md:flex-row gap-6">
                            <div class="flex-1">
                                <h4 class="text-xs font-bold text-blue-400 uppercase mb-1"><i class="fa-solid fa-clipboard-list mr-1"></i> Tema da Entrevista</h4>
                                <p class="text-sm text-slate-200 mb-4">${lead.topic || 'Não definido.'}</p>
                                
                                <h4 class="text-xs font-bold text-blue-400 uppercase mb-1"><i class="fa-solid fa-align-left mr-1"></i> Descrição / Roteiro</h4>
                                <p class="text-sm text-slate-300 whitespace-pre-wrap">${lead.description || 'Nenhum detalhe adicional.'}</p>
                            </div>
                            <div class="w-full md:w-64 bg-slate-900 p-4 rounded-lg border border-slate-700 self-start">
                                <h4 class="text-xs font-bold text-slate-400 uppercase mb-2"><i class="fa-brands fa-whatsapp text-green-500 mr-1"></i> Status de Contato</h4>
                                <select onchange="updateStatus('${lead.profileKey}', this.value)" class="w-full bg-slate-800 border border-slate-600 rounded p-2 text-sm text-white focus:border-blue-500 outline-none">
                                    <option value="whatsapp não enviado" ${selOp1}>Whatsapp não enviado</option>
                                    <option value="mensagem 01 enviada" ${selOp2}>Mensagem 01 enviada</option>
                                    <option value="lead respondeu" ${selOp3}>Lead respondeu</option>
                                    <option value="lead não respondeu" ${selOp4}>Lead não respondeu</option>
                                </select>
                            </div>
                        </div>
                    </td>
                </tr>
                `;
            });
            tbody.innerHTML = html;
        }

        // 8. Logica de Logs
        function addLog(message) {
            const timestamp = new Date().toLocaleTimeString('pt-BR');
            systemLogs.push(`[${timestamp}] ${message}`);
            const container = document.getElementById('logs-container');
            container.innerHTML = systemLogs.map(log => `<div>${log}</div>`).join('');
            container.scrollTop = container.scrollHeight;
        }

        function requestClearLogs() { document.getElementById('confirm-delete-modal').classList.remove('hidden'); }
        function confirmClearLogs() {
            systemLogs = [];
            document.getElementById('logs-container').innerHTML = '';
            closeModal('confirm-delete-modal');
            addLog(`Logs apagados por ${currentSystemUser.name}.`);
        }

        // 9. Adicionar/Excluir Lead
        function openAddLeadModal() {
            document.getElementById('lead-form').reset();
            document.getElementById('lead-modal').classList.remove('hidden');
        }

        function saveLead(e) {
            e.preventDefault();
            const newLead = {
                name: document.getElementById('input-name').value,
                company: document.getElementById('input-company').value,
                role: document.getElementById('input-role').value,
                email: document.getElementById('input-email').value,
                whatsapp: document.getElementById('input-whatsapp').value,
                topic: document.getElementById('input-topic').value,
                description: document.getElementById('input-desc').value,
                linkedin: document.getElementById('input-linkedin').value,
                status: "whatsapp não enviado"
            };
            newLead.profileKey = getLeadProfileKey(newLead);
            leads.push(newLead);
            addLog(`Novo lead '${newLead.name}' adicionado por ${currentSystemUser.name}.`);
            closeModal('lead-modal');
            renderLeadsTable();
        }

        function deleteLead(profileKey) {
            const lead = leads.find(l => l.profileKey === profileKey);
            if (!lead) return;
            if (confirm(`Remover o lead '${lead.name}'?`)) {
                leads = leads.filter(l => l.profileKey !== profileKey);
                addLog(`Lead '${lead.name}' removido por ${currentSystemUser.name}.`);
                renderLeadsTable();
            }
        }

        function closeModal(modalId) { document.getElementById(modalId).classList.add('hidden'); }

        window.onload = initSystem;
    </script>
</body>
</html>
