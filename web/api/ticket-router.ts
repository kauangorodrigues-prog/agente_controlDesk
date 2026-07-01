import { createRouter, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { tickets } from "@db/schema";
import { desc, eq, like, or, and, sql } from "drizzle-orm";
import { z } from "zod";

export const ticketRouter = createRouter({
  list: authedQuery
    .input(
      z.object({
        search: z.string().optional(),
        status: z.string().optional(),
        priority: z.string().optional(),
        page: z.number().min(1).default(1),
        limit: z.number().min(1).max(100).default(10),
      }).optional()
    )
    .query(async ({ input }) => {
      const db = getDb();
      const { search, status, priority, page = 1, limit = 10 } = input ?? {};

      const conditions = [];
      if (status && status !== "all") {
        conditions.push(eq(tickets.status, status as "open" | "in_progress" | "pending" | "resolved" | "closed"));
      }
      if (priority && priority !== "all") {
        conditions.push(eq(tickets.priority, priority as "low" | "medium" | "high" | "critical"));
      }
      if (search) {
        conditions.push(
          or(
            like(tickets.title, `%${search}%`),
            like(tickets.description, `%${search}%`)
          )
        );
      }

      const where = conditions.length > 0 ? and(...conditions) : undefined;

      const totalResult = await db
        .select({ count: sql<number>`count(*)` })
        .from(tickets)
        .where(where);

      const total = totalResult[0]?.count ?? 0;

      const items = await db
        .select()
        .from(tickets)
        .where(where)
        .orderBy(desc(tickets.createdAt))
        .limit(limit)
        .offset((page - 1) * limit);

      return {
        items,
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      };
    }),

  getById: authedQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const result = await db
        .select()
        .from(tickets)
        .where(eq(tickets.id, input.id));
      return result[0] ?? null;
    }),

  create: authedQuery
    .input(
      z.object({
        title: z.string().min(1),
        description: z.string().optional(),
        category: z.enum(["hardware", "software", "network", "security", "access", "other"]),
        priority: z.enum(["low", "medium", "high", "critical"]).default("medium"),
        status: z.enum(["open", "in_progress", "pending", "resolved", "closed"]).default("open"),
        requesterName: z.string().optional(),
        requesterEmail: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const [result] = await db.insert(tickets).values(input);
      return { id: Number(result.insertId) };
    }),

  update: authedQuery
    .input(
      z.object({
        id: z.number(),
        title: z.string().min(1).optional(),
        description: z.string().optional(),
        category: z.enum(["hardware", "software", "network", "security", "access", "other"]).optional(),
        priority: z.enum(["low", "medium", "high", "critical"]).optional(),
        status: z.enum(["open", "in_progress", "pending", "resolved", "closed"]).optional(),
        requesterName: z.string().optional(),
        requesterEmail: z.string().optional(),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const { id, ...data } = input;
      await db.update(tickets).set(data).where(eq(tickets.id, id));
      return { success: true };
    }),

  delete: authedQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(tickets).where(eq(tickets.id, input.id));
      return { success: true };
    }),
});
