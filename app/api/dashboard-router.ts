import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tickets, incidents } from "@db/schema";
import { sql, desc, eq } from "drizzle-orm";

export const dashboardRouter = createRouter({
  stats: publicQuery.query(async () => {
    const db = getDb();

    const totalTickets = await db.select({ count: sql<number>`count(*)` }).from(tickets);
    const openTickets = await db.select({ count: sql<number>`count(*)` }).from(tickets).where(eq(tickets.status, "open"));
    const resolvedTickets = await db.select({ count: sql<number>`count(*)` }).from(tickets).where(eq(tickets.status, "resolved"));
    const criticalIncidents = await db.select({ count: sql<number>`count(*)` }).from(incidents).where(eq(incidents.priority, "critical"));

    return {
      totalTickets: totalTickets[0]?.count ?? 0,
      openTickets: openTickets[0]?.count ?? 0,
      resolvedToday: resolvedTickets[0]?.count ?? 0,
      criticalIncidents: criticalIncidents[0]?.count ?? 0,
    };
  }),

  ticketTrend: publicQuery.query(async () => {
    const db = getDb();

    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d.toISOString().split("T")[0];
    });

    const results = [];
    for (const date of last7Days) {
      const count = await db
        .select({ count: sql<number>`count(*)` })
        .from(tickets)
        .where(sql`DATE(createdAt) = ${date}`);

      results.push({
        date,
        count: count[0]?.count ?? 0,
      });
    }

    return results;
  }),

  ticketsByCategory: publicQuery.query(async () => {
    const db = getDb();

    const results = await db
      .select({
        category: tickets.category,
        count: sql<number>`count(*)`,
      })
      .from(tickets)
      .groupBy(tickets.category);

    return results;
  }),

  ticketsByStatus: publicQuery.query(async () => {
    const db = getDb();

    const results = await db
      .select({
        status: tickets.status,
        count: sql<number>`count(*)`,
      })
      .from(tickets)
      .groupBy(tickets.status);

    return results;
  }),

  recentTickets: publicQuery.query(async () => {
    const db = getDb();

    return db
      .select()
      .from(tickets)
      .orderBy(desc(tickets.createdAt))
      .limit(5);
  }),

  systemStatus: publicQuery.query(async () => {
    return [
      { name: "API Gateway", status: "operational" as const, uptime: "99.9%" },
      { name: "Banco de Dados", status: "operational" as const, uptime: "99.7%" },
      { name: "Servidor de Email", status: "degraded" as const, uptime: "97.2%" },
      { name: "Portal de Clientes", status: "operational" as const, uptime: "99.5%" },
      { name: "Servidor de Arquivos", status: "operational" as const, uptime: "99.8%" },
      { name: "Firewall", status: "operational" as const, uptime: "99.9%" },
    ];
  }),
});
