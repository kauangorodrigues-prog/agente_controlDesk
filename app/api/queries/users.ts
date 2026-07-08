import { eq } from "drizzle-orm";
import * as schema from "@db/schema";
import { sqliteNow } from "@db/schema";
import type { InsertUser } from "@db/schema";
import { getDb } from "./connection";
import { env } from "../lib/env";

export async function findUserByUnionId(unionId: string) {
  const rows = await getDb()
    .select()
    .from(schema.users)
    .where(eq(schema.users.unionId, unionId))
    .limit(1);
  return rows.at(0);
}

export async function findUserByEmail(email: string) {
  const rows = await getDb()
    .select()
    .from(schema.users)
    .where(eq(schema.users.email, email.toLowerCase()))
    .limit(1);
  return rows.at(0);
}

export async function touchLastSignIn(unionId: string) {
  await getDb()
    .update(schema.users)
    .set({ lastSignInAt: sqliteNow() })
    .where(eq(schema.users.unionId, unionId));
}

/**
 * Insert or update a user keyed by unionId. If the email matches the configured
 * owner email, the user is promoted to "admin".
 */
export async function upsertUser(data: InsertUser) {
  const values: InsertUser = { ...data };

  if (
    values.role === undefined &&
    values.email &&
    values.email.toLowerCase() === env.ownerEmail
  ) {
    values.role = "admin";
  }

  const updateSet: Partial<InsertUser> = {
    lastSignInAt: sqliteNow(),
    ...values,
  };

  await getDb()
    .insert(schema.users)
    .values(values)
    .onConflictDoUpdate({ target: schema.users.unionId, set: updateSet });
}
