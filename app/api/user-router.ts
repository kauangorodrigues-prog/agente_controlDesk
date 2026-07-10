import { createRouter, authedQuery, adminQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { users } from "@db/schema";
import { sqliteNow } from "@db/schema";
import { hashPassword } from "./lib/password";
import { findUserByEmail } from "./queries/users";
import { and, desc, eq, ne, sql } from "drizzle-orm";
import { nanoid } from "nanoid";
import { z } from "zod";
import { TRPCError } from "@trpc/server";

const publicUserColumns = {
  id: users.id,
  unionId: users.unionId,
  name: users.name,
  email: users.email,
  avatar: users.avatar,
  role: users.role,
  createdAt: users.createdAt,
  updatedAt: users.updatedAt,
  lastSignInAt: users.lastSignInAt,
};

export const userRouter = createRouter({
  list: authedQuery
    .input(z.object({ search: z.string().optional() }).optional())
    .query(async ({ input }) => {
      const db = getDb();
      const search = input?.search?.trim();
      const rows = await db
        .select(publicUserColumns)
        .from(users)
        .orderBy(desc(users.createdAt));
      if (!search) return rows;
      const q = search.toLowerCase();
      return rows.filter(
        (u) =>
          (u.name ?? "").toLowerCase().includes(q) ||
          (u.email ?? "").toLowerCase().includes(q),
      );
    }),

  stats: authedQuery.query(async () => {
    const db = getDb();
    const [total] = await db
      .select({ c: sql<number>`count(*)` })
      .from(users);
    const [admins] = await db
      .select({ c: sql<number>`count(*)` })
      .from(users)
      .where(eq(users.role, "admin"));
    const [active] = await db
      .select({ c: sql<number>`count(*)` })
      .from(users)
      .where(sql`lastSignInAt >= datetime('now', '-30 days')`);
    return {
      total: total?.c ?? 0,
      admins: admins?.c ?? 0,
      active: active?.c ?? 0,
    };
  }),

  create: adminQuery
    .input(
      z.object({
        name: z.string().min(1).max(255),
        email: z.string().email(),
        password: z.string().min(6),
        role: z.enum(["user", "admin"]).default("user"),
      }),
    )
    .mutation(async ({ input }) => {
      const email = input.email.toLowerCase();
      if (await findUserByEmail(email)) {
        throw new TRPCError({
          code: "CONFLICT",
          message: "Já existe uma conta com este e-mail.",
        });
      }
      const [row] = await getDb()
        .insert(users)
        .values({
          unionId: nanoid(),
          name: input.name,
          email,
          passwordHash: hashPassword(input.password),
          role: input.role,
        })
        .returning({ id: users.id });
      return { id: row.id };
    }),

  updateRole: adminQuery
    .input(z.object({ id: z.number(), role: z.enum(["user", "admin"]) }))
    .mutation(async ({ input, ctx }) => {
      if (input.id === ctx.user.id && input.role !== "admin") {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Você não pode remover seu próprio acesso de administrador.",
        });
      }
      await getDb()
        .update(users)
        .set({ role: input.role, updatedAt: sqliteNow() })
        .where(eq(users.id, input.id));
      return { success: true };
    }),

  remove: adminQuery
    .input(z.object({ id: z.number() }))
    .mutation(async ({ input, ctx }) => {
      if (input.id === ctx.user.id) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Você não pode excluir a sua própria conta.",
        });
      }
      await getDb()
        .delete(users)
        .where(and(eq(users.id, input.id), ne(users.id, ctx.user.id)));
      return { success: true };
    }),
});
