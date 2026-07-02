import { createRouter, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tickets, incidents } from "@db/schema";
import { sql, desc, eq } from "drizzle-orm";

type Trend = { trend: string; trendUp: boolean };

function pctChange(current: number, previous: number): Trend {
  if (previous === 0) {
    return current > 0 ? { trend: "+100%", trendUp: true } : { trend: "0%", trendUp: true };
  }
  const pct = Math.round(((current - previous) / previous) * 100);
  return { trend: `${pct >= 0 ? "+" : ""}${pct}%`, trendUp: pct >= 0 };
}

async function count(
  db: ReturnType<typeof getDb>,
  table: typeof tickets | typeof incidents,
  where: ReturnType<typeof sql>,
) {
  const rows = await db.select({ count: sql<number>`count(*)` }).from(table).where(where);
  return rows[0]?.count ?? 0;
}

export const dashboardRouter = createRouter({
  stats: authedQuery.query(async () => {
    const db = getDb();

    const totalTickets = await db.select({ count: sql<number>`count(*)` }).from(tickets);
    const openTickets = await db.select({ count: sql<number>`count(*)` }).from(tickets).where(eq(tickets.status, "open"));
    const resolvedTodayCount = await count(db, tickets, sql`status = 'resolved' AND DATE(resolvedAt) = CURDATE()`);
    const resolvedYesterdayCount = await count(
      db,
      tickets,
      sql`status = 'resolved' AND DATE(resolvedAt) = CURDATE() - INTERVAL 1 DAY`,
    );
    const criticalIncidents = await db.select({ count: sql<number>`count(*)` }).from(incidents).where(eq(incidents.priority, "critical"));

    // Trends compare the last 7 days against the 7 days before that, using
    // creation timestamps (the only history we actually store — current
    // status/priority is mutable and has no snapshot history to diff against).
    const newTicketsThisWeek = await count(db, tickets, sql`createdAt >= NOW() - INTERVAL 7 DAY`);
    const newTicketsPrevWeek = await count(
      db,
      tickets,
      sql`createdAt >= NOW() - INTERVAL 14 DAY AND createdAt < NOW() - INTERVAL 7 DAY`,
    );

    const newOpenThisWeek = await count(db, tickets, sql`status = 'open' AND createdAt >= NOW() - INTERVAL 7 DAY`);
    const newOpenPrevWeek = await count(
      db,
      tickets,
      sql`status = 'open' AND createdAt >= NOW() - INTERVAL 14 DAY AND createdAt < NOW() - INTERVAL 7 DAY`,
    );

    const newCriticalThisWeek = await count(
      db,
      incidents,
      sql`priority = 'critical' AND createdAt >= NOW() - INTERVAL 7 DAY`,
    );
    const newCriticalPrevWeek = await count(
      db,
      incidents,
      sql`priority = 'critical' AND createdAt >= NOW() - INTERVAL 14 DAY AND createdAt < NOW() - INTERVAL 7 DAY`,
    );

    return {
      totalTickets: totalTickets[0]?.count ?? 0,
      openTickets: openTickets[0]?.count ?? 0,
      resolvedToday: resolvedTodayCount,
      criticalIncidents: criticalIncidents[0]?.count ?? 0,
      trends: {
        totalTickets: pctChange(newTicketsThisWeek, newTicketsPrevWeek),
        openTickets: pctChange(newOpenThisWeek, newOpenPrevWeek),
        resolvedToday: pctChange(resolvedTodayCount, resolvedYesterdayCount),
        criticalIncidents: pctChange(newCriticalThisWeek, newCriticalPrevWeek),
      },
    };
  }),

  ticketTrend: authedQuery.query(async () => {
    const db = getDb();

    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d.toISOString().split("T")[0];
    });

    const rows = await db
      .select({
        date: sql<string>`DATE_FORMAT(createdAt, '%Y-%m-%d')`,
        count: sql<number>`count(*)`,
      })
      .from(tickets)
      .where(sql`createdAt >= CURDATE() - INTERVAL 6 DAY`)
      .groupBy(sql`DATE_FORMAT(createdAt, '%Y-%m-%d')`);

    const byDate = new Map(rows.map((r) => [r.date, r.count]));
    return last7Days.map((date) => ({ date, count: byDate.get(date) ?? 0 }));
  }),

  ticketsByCategory: authedQuery.query(async () => {
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

  ticketsByStatus: authedQuery.query(async () => {
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

  recentTickets: authedQuery.query(async () => {
    const db = getDb();

    return db
      .select()
      .from(tickets)
      .orderBy(desc(tickets.createdAt))
      .limit(5);
  }),

  systemStatus: authedQuery.query(async () => {
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
