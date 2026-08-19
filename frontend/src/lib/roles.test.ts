import { describe, it, expect } from "vitest";
import { hasMinRole, canAccessSector } from "./roles";

describe("hasMinRole", () => {
  it("respeita a hierarquia de papéis", () => {
    expect(hasMinRole("diretoria", "gerencia")).toBe(true);
    expect(hasMinRole("gerencia", "gerencia")).toBe(true);
    expect(hasMinRole("administracao", "gerencia")).toBe(false);
    expect(hasMinRole("administracao", "administracao")).toBe(true);
  });

  it("trata papel ausente ou inválido como sem permissão", () => {
    expect(hasMinRole(undefined, "administracao")).toBe(false);
    expect(hasMinRole("inexistente", "administracao")).toBe(false);
  });
});

describe("canAccessSector", () => {
  it("diretoria acessa qualquer setor", () => {
    expect(canAccessSector("diretoria", [], "mis")).toBe(true);
  });

  it("demais papéis acessam apenas setores concedidos", () => {
    expect(canAccessSector("gerencia", ["control_desk"], "control_desk")).toBe(true);
    expect(canAccessSector("gerencia", ["control_desk"], "mis")).toBe(false);
  });

  it("sem usuário não acessa nada", () => {
    expect(canAccessSector(undefined, [], "mis")).toBe(false);
  });
});
