import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { chatConversations, chatMessages, tickets, sqliteNow } from "@db/schema";
import { desc, eq } from "drizzle-orm";
import { findRelevantArticle } from "./queries/kb";
import { z } from "zod";

// Mock AI responses for IT support
const aiResponses: Record<string, string> = {
  default: `Olá! Sou o assistente virtual do NexusAI Control Desk. Como posso ajudar você hoje?\n\nPosso auxiliar com:\n- Resolução de problemas técnicos\n- Criação e consulta de tickets\n- Análise de incidentes\n- Orientações sobre procedimentos IT\n- Geração de relatórios\n\nDescreva seu problema ou pergunta e farei o possível para ajudar.`,

  server: `Para reiniciar um servidor de forma segura, siga estes passos:\n\n1. **Notifique os usuários** com antecedência\n2. **Verifique conexões ativas** - confirme que não há sessões críticas\n3. **Encerre serviços gracefully** - pare serviços na ordem correta\n4. **Execute o restart** e monitore a inicialização\n5. **Valide após reinício** - teste todos os serviços\n\n**Tempo estimado de indisponibilidade**: 3-5 minutos.\n\nDeseja que eu crie um ticket para documentar este procedimento?`,

  password: `Para redefinir sua senha:\n\n1. Acesse o portal de self-service: **portal.empresa.com/reset**\n2. Informe seu email corporativo\n3. Clique no link enviado para seu email\n4. Crie uma nova senha seguindo as políticas:\n   - Mínimo 8 caracteres\n   - Letras maiúsculas e minúsculas\n   - Pelo menos 1 número e 1 caractere especial\n\nSe não tiver acesso ao email, entre em contato com o suporte pelo ramal 8080.`,

  network: `Problemas de rede podem ter várias causas. Vamos diagnosticar:\n\n**Verificações iniciais:**\n1. O cabo de rede está conectado? (LED piscando na porta)\n2. Reinicie o computador e o switch da mesa\n3. Teste com outro cabo/conexão\n\n**Comandos para diagnosticar:**\n\`ipconfig /flushdns\`\n\`ping 8.8.8.8\`\n\`nslookup portal.empresa.com\`\n\nSe o problema persistir, vou criar um ticket para a equipe de infraestrutura analisar.`,

  vpn: `Para configurar a VPN corporativa:\n\n1. Baixe o cliente **Cisco AnyConnect** no portal de software\n2. Instale com privilégios de administrador\n3. Configure o servidor: **vpn.empresa.com**\n4. Use suas credenciais corporativas (domínio\\\\usuário)\n\n**Problemas comuns:**\n- Erro "Certificate invalid": Instale o certificado raiz corporativo\n- Timeout: Verifique se a porta 443 está liberada no firewall\n- Autenticação falha: Confirme que sua conta tem acesso VPN habilitado\n\nPrecisa de ajuda com algum desses passos?`,

  backup: `Sobre o sistema de backup:\n\n**Frequência:**\n- Incrementais: A cada 4 horas\n- Full: Diariamente às 02:00\n- Retenção: 30 dias\n\n**Para restaurar arquivos:**\n1. Acesse **\\\\backup.empresa.com**\\\\restores\n2. Navegue até a data desejada\n3. Selecione os arquivos e clique em "Restaurar"\n4. Os arquivos serão disponibilizados em até 2h\n\n**Para solicitações urgentes**, crie um ticket com prioridade **Alta** e informe:\n- Caminho completo dos arquivos\n- Data aproximada da última versão conhecida\n- Justificativa da urgência`,

  ticket: `Vou criar um ticket para você. Por favor, forneça:\n\n1. **Título resumido** do problema\n2. **Descrição detalhada** com:\n   - O que está acontecendo\n   - Quando começou\n   - Quem está afetado\n   - Tentativas de resolução\n3. **Categoria** (Hardware/Software/Rede/Segurança/Acesso/Outro)\n4. **Prioridade** (Baixa/Média/Alta/Crítica)\n\nCom essas informações, registrarei o chamado e encaminharei para a equipe responsável.`,
};

function getAIResponse(message: string): string {
  const lower = message.toLowerCase();

  if (lower.includes("servidor") || lower.includes("server") || lower.includes("reiniciar")) {
    return aiResponses.server;
  }
  if (lower.includes("senha") || lower.includes("password") || lower.includes("login")) {
    return aiResponses.password;
  }
  if (lower.includes("rede") || lower.includes("network") || lower.includes("internet") || lower.includes("conexão")) {
    return aiResponses.network;
  }
  if (lower.includes("vpn") || lower.includes("remoto")) {
    return aiResponses.vpn;
  }
  if (lower.includes("backup") || lower.includes("restaurar")) {
    return aiResponses.backup;
  }
  if (lower.includes("ticket") || lower.includes("chamado")) {
    return aiResponses.ticket;
  }

  return `Entendi sua solicitação sobre "${message.substring(0, 50)}..."\n\nBaseado na minha análise, recomendo:\n\n1. **Verifique a documentação interna** no Confluence\n2. **Consulte tickets similares** no histórico\n3. **Se o problema persistir**, posso criar um ticket formal para nossa equipe\n\nPosso ajudar com mais alguma informação ou você gostaria que eu abrisse um chamado?`;
}

export const chatRouter = createRouter({
  getConversations: publicQuery.query(async () => {
    const db = getDb();
    return db
      .select()
      .from(chatConversations)
      .orderBy(desc(chatConversations.updatedAt));
  }),

  createConversation: publicQuery
    .input(z.object({ title: z.string().optional() }).optional())
    .mutation(async ({ input }) => {
      const db = getDb();
      const [conversation] = await db
        .insert(chatConversations)
        .values({ title: input?.title ?? "Nova conversa" })
        .returning({ id: chatConversations.id });
      const convId = conversation.id;

      // Add welcome message
      await db.insert(chatMessages).values({
        conversationId: convId,
        role: "assistant",
        content: aiResponses.default,
      });

      return { id: convId };
    }),

  getHistory: publicQuery
    .input(z.object({ conversationId: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      return db
        .select()
        .from(chatMessages)
        .where(eq(chatMessages.conversationId, input.conversationId))
        .orderBy(chatMessages.createdAt);
    }),

  sendMessage: publicQuery
    .input(
      z.object({
        conversationId: z.number(),
        message: z.string().min(1),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const { conversationId, message } = input;

      // Save user message
      await db.insert(chatMessages).values({
        conversationId,
        role: "user",
        content: message,
      });

      // Generate AI response, enriched with a relevant knowledge base article.
      let aiResponse = getAIResponse(message);
      const article = await findRelevantArticle(message);
      if (article) {
        aiResponse += `\n\n---\n📚 **Artigo relacionado na Base de Conhecimento:** ${article.title}${
          article.summary ? `\n_${article.summary}_` : ""
        }\n(Referência: KB #${article.id})`;
      }

      // Save AI response
      await db.insert(chatMessages).values({
        conversationId,
        role: "assistant",
        content: aiResponse,
      });

      // Update conversation timestamp
      await db
        .update(chatConversations)
        .set({ updatedAt: sqliteNow() })
        .where(eq(chatConversations.id, conversationId));

      return { response: aiResponse };
    }),

  createTicketFromChat: publicQuery
    .input(z.object({ conversationId: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();

      // Get conversation messages
      const messages = await db
        .select()
        .from(chatMessages)
        .where(eq(chatMessages.conversationId, input.conversationId))
        .orderBy(chatMessages.createdAt);

      const userMessages = messages.filter((m) => m.role === "user");
      const description = messages.map((m) => `${m.role}: ${m.content}`).join("\n\n");

      // Create ticket from chat
      const [row] = await db
        .insert(tickets)
        .values({
          title: `Ticket criado via Chat - ${userMessages[0]?.content?.substring(0, 50) ?? "Sem título"}`,
          description: description.substring(0, 4000),
          category: "other",
          status: "open",
          priority: "medium",
        })
        .returning({ id: tickets.id });

      return { ticketId: row.id };
    }),
});
