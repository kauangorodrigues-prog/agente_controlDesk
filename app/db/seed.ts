import { sql } from "drizzle-orm";
import type { SQLiteTable } from "drizzle-orm/sqlite-core";
import { getDb } from "../api/queries/connection";
import { hashPassword } from "../api/lib/password";
import { env } from "../api/lib/env";
import {
  users,
  tickets,
  incidents,
  chatConversations,
  chatMessages,
  activities,
} from "./schema";

/** Default administrator account created on first boot. */
export const DEFAULT_ADMIN = {
  name: "Administrador",
  email: env.ownerEmail,
  password: "admin123",
};

async function count(table: SQLiteTable) {
  const rows = await getDb()
    .select({ c: sql<number>`count(*)` })
    .from(table);
  return rows[0]?.c ?? 0;
}

async function seedUsers() {
  if ((await count(users)) > 0) return;
  await getDb()
    .insert(users)
    .values({
      unionId: "seed-admin",
      name: DEFAULT_ADMIN.name,
      email: DEFAULT_ADMIN.email,
      passwordHash: hashPassword(DEFAULT_ADMIN.password),
      role: "admin",
    });
}

async function seedTickets() {
  if ((await count(tickets)) > 0) return;
  const ticketData = [
    {
      title: "Servidor de email não responde",
      description:
        "O servidor de email Exchange está fora do ar desde 08:30. Usuários não conseguem enviar ou receber emails.",
      category: "network" as const,
      status: "open" as const,
      priority: "critical" as const,
      requesterName: "Carlos Silva",
      requesterEmail: "carlos.silva@empresa.com",
    },
    {
      title: "Instalação de software de desenvolvimento",
      description:
        "Solicito instalação do Visual Studio 2022 e Docker Desktop na máquina DEV-042.",
      category: "software" as const,
      status: "in_progress" as const,
      priority: "medium" as const,
      requesterName: "Ana Pereira",
      requesterEmail: "ana.pereira@empresa.com",
    },
    {
      title: "Troca de teclado defeituoso",
      description:
        "Teclado da estação de trabalho HR-015 apresenta falhas nas teclas de espaço e enter.",
      category: "hardware" as const,
      status: "resolved" as const,
      priority: "low" as const,
      requesterName: "Maria Santos",
      requesterEmail: "maria.santos@empresa.com",
      resolvedAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    },
    {
      title: "Acesso negado ao sistema ERP",
      description:
        "Ao tentar acessar o sistema ERP, recebo mensagem de 'acesso não autorizado'. Necessito acesso ao módulo financeiro.",
      category: "access" as const,
      status: "open" as const,
      priority: "high" as const,
      requesterName: "João Oliveira",
      requesterEmail: "joao.oliveira@empresa.com",
    },
    {
      title: "Suspeita de phishing no email corporativo",
      description:
        "Recebi um email solicitando atualização de senha com link suspeito. Preciso que a equipe de segurança analise.",
      category: "security" as const,
      status: "in_progress" as const,
      priority: "high" as const,
      requesterName: "Fernanda Lima",
      requesterEmail: "fernanda.lima@empresa.com",
    },
    {
      title: "Lentidão na rede Wi-Fi do 3º andar",
      description:
        "A conexão Wi-Fi no 3º andar está muito lenta, dificultando video chamadas e acesso a arquivos na nuvem.",
      category: "network" as const,
      status: "pending" as const,
      priority: "medium" as const,
      requesterName: "Pedro Costa",
      requesterEmail: "pedro.costa@empresa.com",
    },
    {
      title: "Monitor externo não detectado",
      description:
        "Após atualização do Windows, o monitor externo via HDMI não é mais detectado pelo notebook.",
      category: "hardware" as const,
      status: "open" as const,
      priority: "medium" as const,
      requesterName: "Lucia Ferreira",
      requesterEmail: "lucia.ferreira@empresa.com",
    },
    {
      title: "Backup automático falhando",
      description:
        "O sistema de backup reporta falhas desde ontem à noite. Logs indicam erro de conexão com o NAS.",
      category: "software" as const,
      status: "in_progress" as const,
      priority: "high" as const,
      requesterName: "Roberto Almeida",
      requesterEmail: "roberto.almeida@empresa.com",
    },
    {
      title: "Criação de conta para novo colaborador",
      description:
        "Solicito criação de conta de rede e email para Ricardo Mendes, novo analista financeiro.",
      category: "access" as const,
      status: "resolved" as const,
      priority: "medium" as const,
      requesterName: "HR Departamento",
      requesterEmail: "rh@empresa.com",
      resolvedAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    },
    {
      title: "Atualização de certificado SSL",
      description:
        "O certificado SSL do portal interno expira em 3 dias. Necessário renovação.",
      category: "security" as const,
      status: "open" as const,
      priority: "critical" as const,
      requesterName: "Tiago Souza",
      requesterEmail: "tiago.souza@empresa.com",
    },
  ];
  await getDb().insert(tickets).values(ticketData);
}

async function seedIncidents() {
  if ((await count(incidents)) > 0) return;
  const incidentData = [
    {
      title: "Queda total do data center principal",
      description:
        "Data center principal ficou indisponível por 15 minutos devido a falha no UPS. Todos os serviços internos afetados.",
      status: "resolved" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Ataque DDoS no portal de clientes",
      description:
        "Detectado ataque DDoS de alta intensidade contra o portal de clientes. WAF mitigando o ataque.",
      status: "in_progress" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Falha no sistema de backup",
      description:
        "Sistema de backup não executou nos últimos 2 dias. Risco de perda de dados.",
      status: "open" as const,
      priority: "high" as const,
      impact: "department" as const,
    },
    {
      title: "Latência excessiva no banco de dados",
      description:
        "Queries no banco de dados principal apresentando latência 3x acima do normal.",
      status: "in_progress" as const,
      priority: "high" as const,
      impact: "department" as const,
    },
    {
      title: "Vulnerabilidade crítica no Apache",
      description:
        "CVE-2024-XXXX identificada no Apache. Necessário patch imediato.",
      status: "open" as const,
      priority: "critical" as const,
      impact: "company" as const,
    },
    {
      title: "Falha no ar-condicionado do server room",
      description:
        "Temperatura do server room subindo devido a falha no AC. Equipe de facilities acionada.",
      status: "resolved" as const,
      priority: "high" as const,
      impact: "company" as const,
    },
    {
      title: "Spam em massa no email corporativo",
      description:
        "Aumento significativo de emails de spam chegando às caixas de entrada.",
      status: "pending" as const,
      priority: "medium" as const,
      impact: "team" as const,
    },
  ];
  await getDb().insert(incidents).values(incidentData);
}

async function seedChat() {
  if ((await count(chatConversations)) > 0) return;
  const [conversation] = await getDb()
    .insert(chatConversations)
    .values({ title: "Como reiniciar o servidor de arquivos?" })
    .returning({ id: chatConversations.id });

  const convId = conversation.id;

  await getDb()
    .insert(chatMessages)
    .values([
      {
        conversationId: convId,
        role: "user" as const,
        content:
          "Como faço para reiniciar o servidor de arquivos FILE-SRV-01 de forma segura?",
      },
      {
        conversationId: convId,
        role: "assistant" as const,
        content:
          "Para reiniciar o servidor FILE-SRV-01 de forma segura, siga estes passos:\n\n1. **Notifique os usuários** - Envie comunicado com pelo menos 30min de antecedência\n2. **Verifique conexões ativas** - Use `netstat -an` para verificar sessões ativas\n3. **Encerre serviços gracefully**:\n   - Pare o serviço SMB: `Stop-Service LanmanServer`\n   - Pare o DFS: `Stop-Service DFS`\n4. **Execute o restart**: `Restart-Computer -Force`\n5. **Valide após reinício**:\n   - Verifique se serviços iniciaram: `Get-Service LanmanServer,DFS`\n   - Teste acesso aos compartilhamentos\n   - Confirme replicação DFS está sincronizada\n\n**Tempo estimado de indisponibilidade**: 3-5 minutos.\n\nDeseja que eu crie um ticket para documentar este procedimento?",
      },
    ]);
}

async function seedActivities() {
  if ((await count(activities)) > 0) return;
  const activityData = [
    {
      type: "ticket_created" as const,
      description: "Ticket #1 criado: Servidor de email não responde",
    },
    {
      type: "ticket_created" as const,
      description: "Ticket #4 criado: Acesso negado ao sistema ERP",
    },
    {
      type: "incident_created" as const,
      description: "Incidente #2 criado: Ataque DDoS no portal de clientes",
    },
    {
      type: "ticket_updated" as const,
      description: "Ticket #5 atualizado: Status alterado para Em Andamento",
    },
    {
      type: "chat_session" as const,
      description: "Sessão de chat iniciada sobre reinício de servidor",
    },
    {
      type: "incident_resolved" as const,
      description: "Incidente #6 resolvido: Falha no ar-condicionado",
    },
  ];
  await getDb().insert(activities).values(activityData);
}

/**
 * Populate the database with an admin account and demo data. Idempotent — each
 * table is only seeded when empty, so it is safe to run on every boot.
 */
export async function ensureSeeded() {
  await seedUsers();
  await seedTickets();
  await seedIncidents();
  await seedChat();
  await seedActivities();
}

// Allow running `tsx db/seed.ts` (or the build output) directly.
const invokedDirectly =
  typeof process !== "undefined" &&
  process.argv[1] &&
  process.argv[1].includes("seed");

if (invokedDirectly) {
  ensureSeeded()
    .then(() => {
      console.log("Seed completed successfully!");
      process.exit(0);
    })
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
