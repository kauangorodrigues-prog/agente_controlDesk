import { createRouter, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tickets, incidents } from "@db/schema";
import { sql, eq } from "drizzle-orm";
import { z } from "zod";

export const reportRouter = createRouter({
  ticketVolume: authedQuery
    .input(
      z.object({
        days: z.number().min(1).max(365).default(7),
      }).optional()
    )
    .query(async ({ input }) => {
      const db = getDb();
      const days = input?.days ?? 7;

      const dateRange = Array.from({ length: days }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (days - 1 - i));
        return d.toISOString().split("T")[0];
      });

      const createdRows = await db
        .select({
          date: sql<string>`DATE_FORMAT(createdAt, '%Y-%m-%d')`,
          count: sql<number>`count(*)`,
        })
        .from(tickets)
        .where(sql`createdAt >= CURDATE() - INTERVAL ${days - 1} DAY`)
        .groupBy(sql`DATE_FORMAT(createdAt, '%Y-%m-%d')`);

      const resolvedRows = await db
        .select({
          date: sql<string>`DATE_FORMAT(resolvedAt, '%Y-%m-%d')`,
          count: sql<number>`count(*)`,
        })
        .from(tickets)
        .where(sql`status = 'resolved' AND resolvedAt >= CURDATE() - INTERVAL ${days - 1} DAY`)
        .groupBy(sql`DATE_FORMAT(resolvedAt, '%Y-%m-%d')`);

      const createdByDate = new Map(createdRows.map((r) => [r.date, r.count]));
      const resolvedByDate = new Map(resolvedRows.map((r) => [r.date, r.count]));

      return dateRange.map((date) => ({
        date,
        created: createdByDate.get(date) ?? 0,
        resolved: resolvedByDate.get(date) ?? 0,
      }));
    }),

  resolutionTime: authedQuery.query(async () => {
    const db = getDb();

    const categories = ["hardware", "software", "network", "security", "access", "other"] as const;

    const rows = await db
      .select({
        category: tickets.category,
        avg: sql<number>`COALESCE(AVG(TIMESTAMPDIFF(HOUR, createdAt, resolvedAt)), 0)`,
      })
      .from(tickets)
      .groupBy(tickets.category);

    const byCategory = new Map(rows.map((r) => [r.category, r.avg]));

    return categories.map((category) => ({
      category: category.charAt(0).toUpperCase() + category.slice(1),
      hours: Math.round(byCategory.get(category) ?? 0),
    }));
  }),

  priorityDistribution: authedQuery.query(async () => {
    const db = getDb();

    const results = await db
      .select({
        priority: tickets.priority,
        count: sql<number>`count(*)`,
      })
      .from(tickets)
      .groupBy(tickets.priority);

    return results;
  }),

  incidentStatus: authedQuery.query(async () => {
    const db = getDb();

    const results = await db
      .select({
        status: incidents.status,
        count: sql<number>`count(*)`,
      })
      .from(incidents)
      .groupBy(incidents.status);

    return results;
  }),

  summary: authedQuery
    .input(
      z.object({
        days: z.number().min(1).max(365).default(30),
      }).optional()
    )
    .query(async ({ input }) => {
      const db = getDb();
      const days = input?.days ?? 30;

      const totalTickets = await db
        .select({ count: sql<number>`count(*)` })
        .from(tickets)
        .where(sql`createdAt >= DATE_SUB(NOW(), INTERVAL ${days} DAY)`);

      const resolvedTickets = await db
        .select({ count: sql<number>`count(*)` })
        .from(tickets)
        .where(
          sql`status = 'resolved' AND createdAt >= DATE_SUB(NOW(), INTERVAL ${days} DAY)`
        );

      const openTickets = await db
        .select({ count: sql<number>`count(*)` })
        .from(tickets)
        .where(eq(tickets.status, "open"));

      const totalIncidents = await db
        .select({ count: sql<number>`count(*)` })
        .from(incidents)
        .where(sql`createdAt >= DATE_SUB(NOW(), INTERVAL ${days} DAY)`);

      const total = totalTickets[0]?.count ?? 0;
      const resolved = resolvedTickets[0]?.count ?? 0;

      return {
        totalTickets: total,
        resolutionRate: total > 0 ? Math.round((resolved / total) * 100) : 0,
        openTickets: openTickets[0]?.count ?? 0,
        totalIncidents: totalIncidents[0]?.count ?? 0,
      };
    }),
});
