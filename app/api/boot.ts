import app from "./app";
import { env } from "./lib/env";
import { ensureSeeded } from "@db/seed";

// Initialise the embedded SQLite database (create tables + seed demo data).
await ensureSeeded();

export default app;

if (env.isProduction) {
  const { serve } = await import("@hono/node-server");
  const { serveStaticFiles } = await import("./lib/vite");
  serveStaticFiles(app);

  const port = parseInt(process.env.PORT || "3000");
  serve({ fetch: app.fetch, port }, () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}
