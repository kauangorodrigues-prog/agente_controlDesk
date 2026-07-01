import { createRouter, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { incidents } from "@db/schema";
import { desc, eq, and } from "drizzle-orm";
import { z } from "zod";

export const incidentRouter = createRouter({
  list: authedQuery
    .input(
      z.object({
        status: z.string().optional(),
        priority: z.string().optional(),
      }).optional()
    )
    .query(async ({ input }) => {
      const db = getDb();
      const { status, priority } = input ?? {};

      const conditions = [];
      if (status && status !== "all") {
        conditions.push(eq(incidents.status, status as "open" | "in_progress" | "pending" | "resolved"));
      }
      if (priority && priority !== "all") {
        conditions.push(eq(incidents.priority, priority as "low" | "medium" | "high" | "critical"));
      }

      const where = conditions.length > 0 ? and(...conditions) : undefined;

      return db
        .select()
        .from(incidents)
        .where(where)
        .orderBy(desc(incidents.createdAt));
    }),

  create: authedQuery
    .input(
      z.object({
        title: z.string().min(1),
        description: z.string().optional(),
        priority: z.enum(["low", "medium", "high", "critical"]).default("medium"),
        impact: z.enum(["individual", "team", "department", "company"]).default("individual"),
        status: z.enum(["open", "in_progress", "pending", "resolved"]).default("open"),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const [result] = await db.insert(incidents).values(input);
      return { id: Number(result.insertId) };
    }),

  update: authedQuery
    .input(
      z.object({
        id: z.number(),
        title: z.string().min(1).optional(),
        description: z.string().optional(),
        priority: z.enum(["low", "medium", "high", "critical"]).optional(),
        impact: z.enum(["individual", "team", "department", "company"]).optional(),
        status: z.enum(["open", "in_progress", "pending", "resolved"]).optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const { id, ...data } = input;
      await db.update(incidents).set(data).where(eq(incidents.id, id));
      return { success: true };
    }),

  delete: authedQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(incidents).where(eq(incidents.id, input.id));
      return { success: true };
    }),
});
