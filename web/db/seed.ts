import { getDb } from "../api/queries/connection";
import { tickets, incidents, chatConversations, chatMessages, activities } from "./schema";

async function seed() {
  const db = getDb();

  // Seed tickets
  const ticketData = [
    {
      title: "Servidor de email não responde",
      description: "O servidor de email Exchange está fora do ar desde 08:30. Usuários não conseguem enviar ou receber emails.",
      category: "network" as const,
      status: "open" as const,
      priority: "critical" as const,
      requesterName: "Carlos Silva",
      requesterEmail: "carlos.silva@empresa.com",
    },
    {
      title: "Instalação de software de desenvolvimento",
      description: "Solicito instalação do Visual Studio 2022 e Docker Desktop na máquina DEV-042.",
      category: "software" as const,
      status: "in_progress" as const,
      priority: "medium" as const,
      requesterName: "Ana Pereira",
      requesterEmail: "ana.pereira@empresa.com",
    },
    {
      title: "Troca de teclado defeituoso",
      description: "Teclado da estação de trabalho HR-015 apresenta falhas nas teclas de espaço e enter.",
      category: "hardware" as const,
      status: "resolved" as const,
      priority: "low" as const,
      requesterName: "Maria Santos",
      requesterEmail: "maria.santos@empresa.com",
    },
    {
      title: "Acesso negado ao sistema ERP",
      description: "Ao tentar acessar o sistema ERP, recebo mensagem de 'acesso não autorizado'. Necessito acesso ao módulo financeiro.",
      category: "access" as const,
      status: "open" as const,
      priority: "high" as const,
      requesterName: "João Oliveira",
      requesterEmail: "joao.oliveira@empresa.com",
    },
    {
      title: "Suspeita de phishing no email corporativo",
      description: "Recebi um email solicitando atualização de senha com link suspeito. Preciso que a equipe de segurança analise.",
      category: "security" as const,
      status: "in_progress" as const,
      priority: "high" as const,
      requesterName: "Fernanda Lima",
      requesterEmail: "fernanda.lima@empresa.com",
    },
    {
      title: " Lentidão na rede Wi-Fi do 3º andar",
      description: "A conexão Wi-Fi no 3º andar está muito lenta, dificultando video chamadas e acesso a arquivos na nuvem.",
      category: "network" as const,
      status: "pending" as const,
      priority: "medium" as const,
      requesterName: "Pedro Costa",
      requesterEmail: "pedro.costa@empresa.com",
    },
    {
      title: "Monitor externo não detectado",
      description: "Após atualização do Windows, o monitor externo via HDMI não é mais detectado pelo notebook.",
      category: "hardware" as const,
      status: "open" as const,
      priority: "medium" as const,
      requesterName: "Lucia Ferreira",
      requesterEmail: "lucia.ferreira@empresa.com",
    },
    {
      title: "Backup automático falhando",
      description: "O sistema de backup reporta falhas desde ontem à noite. Logs indicam erro de conexão com o NAS.",
      category: "software" as const,
      status: "in_progress" as const,
      priority: "high" as const,
      requesterName: "Roberto Almeida",
      requesterEmail: "roberto.almeida@empresa.com",
    },
    {
      title: "Criação de conta para novo colaborador",
      description: "Solicito criação de conta de rede e email para Ricardo Mendes, novo analista financeiro.",
      category: "access" as const,
      status: "resolved" as const,
      priority: "medium" as const,
      requesterName: "HR Departamento",
      requesterEmail: "rh@empresa.com",
    },
    {
      title: "Atualização de certificado SSL",
      description: "O certificado SSL do portal interno expira em 3 dias. Necessário renovação.",
      category: "security" as const,
      status: "open" as const,
      priority: "critical" as const,
      requesterName: "Tiago Souza",
      requesterEmail: "tiago.souza@empresa.com",
    },
  ];

  for (const ticket of ticketData) {
    await db.insert(tickets).values(ticket);
  }

  // Seed incidents
  const incidentData = [
    {
      title: "Queda total do data center principal",
      description: "Data center principal ficou indisponível por 15 minutos devido a falha no UPS. Todos os serviços internos afetados.",
      status: "resolved" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Ataque DDoS no portal de clientes",
      description: "Detectado ataque DDoS de alta intensidade contra o portal de clientes. WAF mitigando o ataque.",
      status: "in_progress" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Falha no sistema de backup",
      description: "Sistema de backup não executou nos últimos 2 dias. Risco de perda de dados.",
      status: "open" as const,
      priority: "high" as const,
      impact: "department" as const,
    },
    {
      title: "Latência excessiva no banco de dados",
      description: "Queries no banco de dados principal apresentando latência 3x acima do normal.",
      status: "in_progress" as const,
      priority: "high" as const,
      impact: "department" as const,
    },
    {
      title: "Vulnerabilidade crítica no Apache",
      description: "CVE-2024-XXXX identificada no Apache. Necessário patch imediato.",
      status: "open" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Falha no ar-condicionado do server room",
      description: "Temperatura do server room subindo devido a falha no AC. Equipe de facilities acionada.",
      status: "resolved" as const,
      priority: "high" as const,
      impact: "company" as const,
    },
    {
      title: "Spam em massa no email corporativo",
      description: "Aumento significativo de emails de spam chegando às caixas de entrada.",
      status: "pending" as const,
      priority: "medium" as const,
      impact: "team" as const,
    },
  ];

  for (const incident of incidentData) {
    await db.insert(incidents).values(incident);
  }

  // Seed a sample chat conversation
  const [conversation] = await db.insert(chatConversations).values({
    title: "Como reiniciar o servidor de arquivos?",
  });

  const convId = Number(conversation.insertId);

  await db.insert(chatMessages).values([
    {
      conversationId: convId,
      role: "user",
      content: "Como faço para reiniciar o servidor de arquivos FILE-SRV-01 de forma segura?",
    },
    {
      conversationId: convId,
      role: "assistant",
      content: "Para reiniciar o servidor FILE-SRV-01 de forma segura, siga estes passos:\n\n1. **Notifique os usuários** - Envie comunicado com pelo menos 30min de antecedência\n2. **Verifique conexões ativas** - Use `netstat -an` para verificar sessões ativas\n3. **Encerre serviços gracefully**:\n   - Pare o serviço SMB: `Stop-Service LanmanServer`\n   - Pare o DFS: `Stop-Service DFS`\n4. **Execute o restart**: `Restart-Computer -Force`\n5. **Valide após reinício**:\n   - Verifique se serviços iniciaram: `Get-Service LanmanServer,DFS`\n   - Teste acesso aos compartilhamentos\n   - Confirme replicação DFS está sincronizada\n\n**Tempo estimado de indisponibilidade**: 3-5 minutos.\n\nDeseja que eu crie um ticket para documentar este procedimento?",
    },
  ]);

  // Seed activities
  const activityData = [
    { type: "ticket_created" as const, description: "Ticket #1 criado: Servidor de email não responde" },
    { type: "ticket_created" as const, description: "Ticket #4 criado: Acesso negado ao sistema ERP" },
    { type: "incident_created" as const, description: "Incidente #2 criado: Ataque DDoS no portal de clientes" },
    { type: "ticket_updated" as const, description: "Ticket #5 atualizado: Status alterado para Em Andamento" },
    { type: "chat_session" as const, description: "Sessão de chat iniciada sobre reinício de servidor" },
    { type: "incident_resolved" as const, description: "Incidente #6 resolvido: Falha no ar-condicionado" },
  ];

  for (const activity of activityData) {
    await db.insert(activities).values(activity);
  }

  console.log("Seed completed successfully!");
}

seed().catch(console.error);
