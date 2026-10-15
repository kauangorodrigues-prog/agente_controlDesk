import * as cookie from "cookie";
import { nanoid } from "nanoid";
import { z } from "zod";
import { TRPCError } from "@trpc/server";
import { Session } from "@contracts/constants";
import type { User } from "@db/schema";
import { getSessionCookieOptions } from "./lib/cookies";
import { hashPassword, verifyPassword } from "./lib/password";
import { signSessionToken } from "./kimi/session";
import { env } from "./lib/env";
import {
  findUserByEmail,
  findUserByUnionId,
  touchLastSignIn,
} from "./queries/users";
import { getDb } from "./queries/connection";
import { users } from "@db/schema";
import { createRouter, publicQuery, authedQuery } from "./middleware";

/** Remove sensitive fields before returning a user to the client. */
function sanitize(user: User) {
  const { passwordHash: _passwordHash, ...safe } = user;
  return safe;
}

function setSessionCookie(
  resHeaders: Headers,
  reqHeaders: Headers,
  token: string,
) {
  const opts = getSessionCookieOptions(reqHeaders);
  resHeaders.append(
    "set-cookie",
    cookie.serialize(Session.cookieName, token, {
      httpOnly: opts.httpOnly,
      path: opts.path,
      sameSite: opts.sameSite?.toLowerCase() as "lax" | "none",
      secure: opts.secure,
      maxAge: Session.maxAgeMs / 1000,
    }),
  );
}

async function issueSession(
  ctx: { req: Request; resHeaders: Headers },
  unionId: string,
) {
  const token = await signSessionToken({ unionId, clientId: env.appId });
  setSessionCookie(ctx.resHeaders, ctx.req.headers, token);
}

export const authRouter = createRouter({
  me: authedQuery.query((opts) => sanitize(opts.ctx.user)),

  register: publicQuery
    .input(
      z.object({
        name: z.string().min(1, "Nome obrigatório").max(255),
        email: z.string().email("E-mail inválido"),
        password: z.string().min(6, "A senha deve ter ao menos 6 caracteres"),
      }),
    )
    .mutation(async ({ input, ctx }) => {
      const email = input.email.toLowerCase();
      const existing = await findUserByEmail(email);
      if (existing) {
        throw new TRPCError({
          code: "CONFLICT",
          message: "Já existe uma conta com este e-mail.",
        });
      }

      const unionId = nanoid();
      const role = email === env.ownerEmail ? "admin" : "user";

      await getDb().insert(users).values({
        unionId,
        name: input.name,
        email,
        passwordHash: hashPassword(input.password),
        role,
      });

      await issueSession(ctx, unionId);
      const created = await findUserByUnionId(unionId);
      return created ? sanitize(created) : null;
    }),

  login: publicQuery
    .input(
      z.object({
        email: z.string().email("E-mail inválido"),
        password: z.string().min(1, "Informe a senha"),
      }),
    )
    .mutation(async ({ input, ctx }) => {
      const user = await findUserByEmail(input.email.toLowerCase());
      if (!user || !verifyPassword(input.password, user.passwordHash)) {
        throw new TRPCError({
          code: "UNAUTHORIZED",
          message: "E-mail ou senha inválidos.",
        });
      }

      await touchLastSignIn(user.unionId);
      await issueSession(ctx, user.unionId);
      return sanitize(user);
    }),

  logout: authedQuery.mutation(async ({ ctx }) => {
    const opts = getSessionCookieOptions(ctx.req.headers);
    ctx.resHeaders.append(
      "set-cookie",
      cookie.serialize(Session.cookieName, "", {
        httpOnly: opts.httpOnly,
        path: opts.path,
        sameSite: opts.sameSite?.toLowerCase() as "lax" | "none",
        secure: opts.secure,
        maxAge: 0,
      }),
    );
    return { success: true };
  }),
});
