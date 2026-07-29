// Lógica de papéis (RBAC) pura e testável, compartilhada pela UI.

export type Role = "diretoria" | "gerencia" | "administracao";

export const ROLE_LEVEL: Record<Role, number> = {
  administracao: 1,
  gerencia: 2,
  diretoria: 3,
};

/** True se `role` possui nível >= ao `required` na hierarquia. */
export function hasMinRole(role: string | undefined, required: Role): boolean {
  if (!role) return false;
  const level = ROLE_LEVEL[role as Role];
  return level !== undefined && level >= ROLE_LEVEL[required];
}

/** True se o usuário (papel + setores) pode acessar o setor informado. */
export function canAccessSector(
  role: string | undefined,
  sectors: string[],
  sector: string
): boolean {
  if (!role) return false;
  return role === "diretoria" || sectors.includes(sector);
}
