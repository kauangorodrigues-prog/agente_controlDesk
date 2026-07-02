import { describe, expect, it } from "vitest";
import { getAIResponse } from "./chat-router";

describe("getAIResponse", () => {
  it("matches server/restart related messages", () => {
    expect(getAIResponse("Preciso reiniciar o servidor")).toContain("reiniciar um servidor");
  });

  it("matches password related messages", () => {
    expect(getAIResponse("esqueci minha senha")).toContain("redefinir sua senha");
  });

  it("matches network related messages", () => {
    expect(getAIResponse("estou sem conexão de rede")).toContain("Problemas de rede");
  });

  it("matches vpn related messages", () => {
    expect(getAIResponse("como configuro a vpn")).toContain("VPN corporativa");
  });

  it("matches backup related messages", () => {
    expect(getAIResponse("preciso restaurar um backup")).toContain("sistema de backup");
  });

  it("matches ticket related messages", () => {
    expect(getAIResponse("quero abrir um chamado")).toContain("Vou criar um ticket");
  });

  it("falls back to a generic response for unmatched messages", () => {
    const response = getAIResponse("xyz totalmente fora do escopo");
    expect(response).toContain("xyz totalmente fora do escopo");
    expect(response).toContain("Verifique a documentação interna");
  });

  it("is case-insensitive", () => {
    expect(getAIResponse("SERVIDOR TRAVADO")).toContain("reiniciar um servidor");
  });
});
