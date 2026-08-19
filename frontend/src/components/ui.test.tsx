import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge, money } from "./ui";

describe("money", () => {
  it("formata valores em BRL", () => {
    const out = money(1234.5);
    expect(out).toContain("R$");
    expect(out).toContain("1.234,50");
  });
});

describe("Badge", () => {
  it("renderiza o texto do status", () => {
    render(<Badge value="quitada" />);
    expect(screen.getByText("quitada")).toBeInTheDocument();
  });

  it("aplica a classe de cor mapeada", () => {
    render(<Badge value="aberto" />);
    expect(screen.getByText("aberto").className).toContain("red");
  });
});
