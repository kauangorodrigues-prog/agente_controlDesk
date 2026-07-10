import type { IncomingMessage, ServerResponse } from "node:http";
import { getRequestListener } from "@hono/node-server";
import app from "./api/app";
import { ensureSeeded } from "./db/seed";

// Vercel serverless entrypoint. Bridges Hono's web-standard fetch handler to the
// Node (req, res) signature that @vercel/node expects, and lazily seeds the DB
// on the first request of each cold start.
let seeded: Promise<void> | null = null;
const listener = getRequestListener(app.fetch);

export default async function handler(
  req: IncomingMessage,
  res: ServerResponse,
) {
  if (!seeded) seeded = ensureSeeded();
  await seeded;
  return listener(req, res);
}
