import { createRouter, publicQuery, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { knowledgeArticles, KB_CATEGORIES } from "@db/schema";
import { sqliteNow } from "@db/schema";
import { and, desc, eq, like, or, sql } from "drizzle-orm";
import { z } from "zod";

const categoryEnum = z.enum(KB_CATEGORIES);

export const kbRouter = createRouter({
  list: publicQuery
    .input(
      z
        .object({
          search: z.string().optional(),
          category: z.string().optional(),
          status: z.enum(["all", "draft", "published"]).default("published"),
        })
        .optional(),
    )
    .query(async ({ input }) => {
      const db = getDb();
      const { search, category, status = "published" } = input ?? {};

      const conditions = [];
      if (status !== "all") {
        conditions.push(eq(knowledgeArticles.status, status));
      }
      if (category && category !== "all") {
        conditions.push(
          eq(
            knowledgeArticles.category,
            category as (typeof KB_CATEGORIES)[number],
          ),
        );
      }
      if (search) {
        conditions.push(
          or(
            like(knowledgeArticles.title, `%${search}%`),
            like(knowledgeArticles.summary, `%${search}%`),
            like(knowledgeArticles.content, `%${search}%`),
            like(knowledgeArticles.tags, `%${search}%`),
          ),
        );
      }

      const where = conditions.length > 0 ? and(...conditions) : undefined;

      return db
        .select()
        .from(knowledgeArticles)
        .where(where)
        .orderBy(desc(knowledgeArticles.updatedAt));
    }),

  categories: publicQuery.query(async () => {
    const db = getDb();
    const rows = await db
      .select({
        category: knowledgeArticles.category,
        count: sql<number>`count(*)`,
      })
      .from(knowledgeArticles)
      .where(eq(knowledgeArticles.status, "published"))
      .groupBy(knowledgeArticles.category);
    return rows;
  }),

  getById: publicQuery
    .input(z.object({ id: z.number(), track: z.boolean().default(true) }))
    .query(async ({ input }) => {
      const db = getDb();
      if (input.track) {
        await db
          .update(knowledgeArticles)
          .set({ views: sql`${knowledgeArticles.views} + 1` })
          .where(eq(knowledgeArticles.id, input.id));
      }
      const rows = await db
        .select()
        .from(knowledgeArticles)
        .where(eq(knowledgeArticles.id, input.id));
      return rows[0] ?? null;
    }),

  create: authedQuery
    .input(
      z.object({
        title: z.string().min(1),
        summary: z.string().optional(),
        content: z.string().min(1),
        category: categoryEnum.default("geral"),
        tags: z.string().optional(),
        status: z.enum(["draft", "published"]).default("published"),
      }),
    )
    .mutation(async ({ input, ctx }) => {
      const db = getDb();
      const [row] = await db
        .insert(knowledgeArticles)
        .values({
          ...input,
          authorId: ctx.user.id,
          authorName: ctx.user.name ?? undefined,
        })
        .returning({ id: knowledgeArticles.id });
      return { id: row.id };
    }),

  update: authedQuery
    .input(
      z.object({
        id: z.number(),
        title: z.string().min(1).optional(),
        summary: z.string().optional(),
        content: z.string().min(1).optional(),
        category: categoryEnum.optional(),
        tags: z.string().optional(),
        status: z.enum(["draft", "published"]).optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const { id, ...data } = input;
      await db
        .update(knowledgeArticles)
        .set({ ...data, updatedAt: sqliteNow() })
        .where(eq(knowledgeArticles.id, id));
      return { success: true };
    }),

  delete: authedQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db
        .delete(knowledgeArticles)
        .where(eq(knowledgeArticles.id, input.id));
      return { success: true };
    }),
});
