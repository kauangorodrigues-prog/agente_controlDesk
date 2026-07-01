import { createRouter, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tickets, incidents } from "@db/schema";
import { sql, eq } from "drizzle-orm";
import { z } from "zod";

export const reportRouter = createRouter({
  ticketVolume: authedQuery
    .input(
      z.object({
        days: z.number().default(7),
      }).optional()
    )
    .query(async ({ input }) => {
      const db = getDb();
      const days = input?.days ?? 7;

      const results = [];
      for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const dateStr = d.toISOString().split("T")[0];

        const created = await db
          .select({ count: sql<number>`count(*)` })
          .from(tickets)
          .where(sql`DATE(createdAt) = ${dateStr}`);

        const resolved = await db
          .select({ count: sql<number>`count(*)` })
          .from(tickets)
          .where(
            sql`DATE(resolvedAt) = ${dateStr} AND status = 'resolved'`
          );

        results.push({
          date: dateStr,
          created: created[0]?.count ?? 0,
          resolved: resolved[0]?.count ?? 0,
        });
      }

      return results;
    }),

  resolutionTime: authedQuery.query(async () => {
    const db = getDb();

    const categories = ["hardware", "software", "network", "security", "access", "other"] as const;
    const results = [];

    for (const category of categories) {
      const avgTime = await db
        .select({
          avg: sql<number>`COALESCE(AVG(TIMESTAMPDIFF(HOUR, createdAt, resolvedAt)), 0)`,
        })
        .from(tickets)
        .where(eq(tickets.category, category));

      results.push({
        category: category.charAt(0).toUpperCase() + category.slice(1),
        hours: Math.round(avgTime[0]?.avg ?? 0),
      });
    }

    return results;
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
        days: z.number().default(30),
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
