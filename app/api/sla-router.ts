import { createRouter, publicQuery, adminQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { slaPolicies, tickets, SLA_PRIORITIES } from "@db/schema";
import { sqliteNow } from "@db/schema";
import type { Ticket } from "@db/schema";
import { eq, inArray } from "drizzle-orm";
import { z } from "zod";

type Priority = (typeof SLA_PRIORITIES)[number];

/** Parse a stored SQLite datetime string (UTC) into epoch millis. */
function parseUtc(value?: string | null): number | null {
  if (!value) return null;
  const iso = value.includes("T") ? value : value.replace(" ", "T") + "Z";
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}

const ACTIVE_STATUSES = ["open", "in_progress", "pending"] as const;

export const slaRouter = createRouter({
  policies: publicQuery.query(async () => {
    const db = getDb();
    const rows = await db.select().from(slaPolicies);
    // Return in a stable priority order.
    const order: Priority[] = ["critical", "high", "medium", "low"];
    return rows.sort(
      (a, b) =>
        order.indexOf(a.priority as Priority) -
        order.indexOf(b.priority as Priority),
    );
  }),

  updatePolicy: adminQuery
    .input(
      z.object({
        priority: z.enum(SLA_PRIORITIES),
        responseHours: z.number().int().min(1).max(2160),
        resolutionHours: z.number().int().min(1).max(8760),
      }),
    )
    .mutation(async ({ input }) => {
      await getDb()
        .update(slaPolicies)
        .set({
          responseHours: input.responseHours,
          resolutionHours: input.resolutionHours,
          updatedAt: sqliteNow(),
        })
        .where(eq(slaPolicies.priority, input.priority));
      return { success: true };
    }),

  overview: publicQuery.query(async () => {
    const db = getDb();
    const policies = await db.select().from(slaPolicies);
    const resolutionByPriority = new Map<string, number>(
      policies.map((p) => [p.priority, p.resolutionHours]),
    );

    const activeTickets = await db
      .select()
      .from(tickets)
      .where(inArray(tickets.status, [...ACTIVE_STATUSES]));

    const now = Date.now();
    const HOUR = 3_600_000;

    const evaluate = (t: Ticket) => {
      const created = parseUtc(t.createdAt) ?? now;
      const resolutionHours = resolutionByPriority.get(t.priority) ?? 24;
      const dueAt = created + resolutionHours * HOUR;
      const hoursRemaining = (dueAt - now) / HOUR;
      let slaStatus: "ok" | "at_risk" | "breached";
      if (hoursRemaining <= 0) slaStatus = "breached";
      else if (hoursRemaining <= resolutionHours * 0.25) slaStatus = "at_risk";
      else slaStatus = "ok";
      return {
        id: t.id,
        title: t.title,
        priority: t.priority,
        status: t.status,
        createdAt: t.createdAt,
        dueAt: new Date(dueAt).toISOString(),
        hoursRemaining: Math.round(hoursRemaining * 10) / 10,
        resolutionHours,
        slaStatus,
      };
    };

    const rows = activeTickets
      .map(evaluate)
      .sort((a, b) => a.hoursRemaining - b.hoursRemaining);

    const summary = {
      total: rows.length,
      ok: rows.filter((r) => r.slaStatus === "ok").length,
      atRisk: rows.filter((r) => r.slaStatus === "at_risk").length,
      breached: rows.filter((r) => r.slaStatus === "breached").length,
    };
    const compliance =
      summary.total > 0
        ? Math.round(((summary.total - summary.breached) / summary.total) * 100)
        : 100;

    return { summary, compliance, tickets: rows };
  }),
});
