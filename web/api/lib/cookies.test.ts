import { describe, expect, it } from "vitest";
import { getSessionCookieOptions } from "./cookies";

describe("getSessionCookieOptions", () => {
  it("uses Lax + non-secure cookies for localhost (HTTP dev)", () => {
    const opts = getSessionCookieOptions(new Headers({ host: "localhost:3000" }));
    expect(opts).toMatchObject({ httpOnly: true, path: "/", sameSite: "Lax", secure: false });
  });

  it("uses Lax + non-secure cookies for 127.0.0.1 (HTTP dev)", () => {
    const opts = getSessionCookieOptions(new Headers({ host: "127.0.0.1:3000" }));
    expect(opts).toMatchObject({ sameSite: "Lax", secure: false });
  });

  it("uses None + secure cookies for real hostnames (HTTPS prod)", () => {
    const opts = getSessionCookieOptions(new Headers({ host: "control-desk.empresa.com" }));
    expect(opts).toMatchObject({ httpOnly: true, path: "/", sameSite: "None", secure: true });
  });

  it("treats a missing host header as non-localhost", () => {
    const opts = getSessionCookieOptions(new Headers());
    expect(opts).toMatchObject({ sameSite: "None", secure: true });
  });
});
