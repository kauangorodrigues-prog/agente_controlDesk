import { createRouter, publicQuery, authedQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { assets, ASSET_TYPES, ASSET_STATUSES } from "@db/schema";
import { sqliteNow } from "@db/schema";
import { and, desc, eq, like, or, sql } from "drizzle-orm";
import { z } from "zod";

const typeEnum = z.enum(ASSET_TYPES);
const statusEnum = z.enum(ASSET_STATUSES);

export const assetRouter = createRouter({
  list: publicQuery
    .input(
      z
        .object({
          search: z.string().optional(),
          type: z.string().optional(),
          status: z.string().optional(),
        })
        .optional(),
    )
    .query(async ({ input }) => {
      const db = getDb();
      const { search, type, status } = input ?? {};

      const conditions = [];
      if (type && type !== "all") {
        conditions.push(eq(assets.type, type as (typeof ASSET_TYPES)[number]));
      }
      if (status && status !== "all") {
        conditions.push(
          eq(assets.status, status as (typeof ASSET_STATUSES)[number]),
        );
      }
      if (search) {
        conditions.push(
          or(
            like(assets.name, `%${search}%`),
            like(assets.tag, `%${search}%`),
            like(assets.serialNumber, `%${search}%`),
            like(assets.assignedName, `%${search}%`),
            like(assets.location, `%${search}%`),
          ),
        );
      }

      const where = conditions.length > 0 ? and(...conditions) : undefined;

      return db
        .select()
        .from(assets)
        .where(where)
        .orderBy(desc(assets.createdAt));
    }),

  stats: publicQuery.query(async () => {
    const db = getDb();
    const [total] = await db
      .select({ c: sql<number>`count(*)` })
      .from(assets);
    const byStatus = await db
      .select({ status: assets.status, count: sql<number>`count(*)` })
      .from(assets)
      .groupBy(assets.status);
    const map = Object.fromEntries(byStatus.map((r) => [r.status, r.count]));
    return {
      total: total?.c ?? 0,
      ativo: map["ativo"] ?? 0,
      em_manutencao: map["em_manutencao"] ?? 0,
      em_estoque: map["em_estoque"] ?? 0,
      aposentado: map["aposentado"] ?? 0,
    };
  }),

  getById: publicQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const rows = await db
        .select()
        .from(assets)
        .where(eq(assets.id, input.id));
      return rows[0] ?? null;
    }),

  create: authedQuery
    .input(
      z.object({
        name: z.string().min(1),
        tag: z.string().optional(),
        type: typeEnum.default("outro"),
        status: statusEnum.default("ativo"),
        serialNumber: z.string().optional(),
        location: z.string().optional(),
        assignedTo: z.number().nullable().optional(),
        assignedName: z.string().optional(),
        purchaseDate: z.string().optional(),
        notes: z.string().optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const [row] = await db
        .insert(assets)
        .values(input)
        .returning({ id: assets.id });
      return { id: row.id };
    }),

  update: authedQuery
    .input(
      z.object({
        id: z.number(),
        name: z.string().min(1).optional(),
        tag: z.string().optional(),
        type: typeEnum.optional(),
        status: statusEnum.optional(),
        serialNumber: z.string().optional(),
        location: z.string().optional(),
        assignedTo: z.number().nullable().optional(),
        assignedName: z.string().optional(),
        purchaseDate: z.string().optional(),
        notes: z.string().optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const db = getDb();
      const { id, ...data } = input;
      await db
        .update(assets)
        .set({ ...data, updatedAt: sqliteNow() })
        .where(eq(assets.id, id));
      return { success: true };
    }),

  delete: authedQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input }) => {
      const db = getDb();
      await db.delete(assets).where(eq(assets.id, input.id));
      return { success: true };
    }),
});
