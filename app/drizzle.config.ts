import "dotenv/config";
import { defineConfig } from "drizzle-kit";

// The app auto-creates its SQLite schema on boot (see api/queries/connection.ts),
// so drizzle-kit is optional. These settings let you still run `db:push` /
// `db:generate` against the local SQLite file if you prefer migrations.
const url = process.env.DATABASE_URL?.replace(/^sqlite:\/\//, "").replace(/^file:/, "") ||
  "data/controldesk.db";

export default defineConfig({
  schema: "./db/schema.ts",
  out: "./db/migrations",
  dialect: "sqlite",
  dbCredentials: { url },
});
