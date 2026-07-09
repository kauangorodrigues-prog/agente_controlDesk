import { authRouter } from "./auth-router";
import { dashboardRouter } from "./dashboard-router";
import { ticketRouter } from "./ticket-router";
import { incidentRouter } from "./incident-router";
import { chatRouter } from "./chat-router";
import { reportRouter } from "./report-router";
import { kbRouter } from "./kb-router";
import { createRouter, publicQuery } from "./middleware";

export const appRouter = createRouter({
  ping: publicQuery.query(() => ({ ok: true, ts: Date.now() })),
  auth: authRouter,
  dashboard: dashboardRouter,
  ticket: ticketRouter,
  incident: incidentRouter,
  chat: chatRouter,
  report: reportRouter,
  kb: kbRouter,
});

export type AppRouter = typeof appRouter;
