import { useState } from "react";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";
import {
  Users,
  ShieldCheck,
  Activity,
  Plus,
  Trash2,
  Search,
  Loader2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type NewUser = {
  name: string;
  email: string;
  password: string;
  role: "user" | "admin";
};

const emptyUser: NewUser = {
  name: "",
  email: "",
  password: "",
  role: "user",
};

function initials(name?: string | null) {
  if (!name) return "?";
  return name
    .split(" ")
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("");
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const d = new Date(value.includes("T") ? value : value.replace(" ", "T") + "Z");
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export default function Equipe() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const utils = trpc.useUtils();

  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<NewUser>(emptyUser);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const { data: members, isLoading } = trpc.user.list.useQuery({
    search: search || undefined,
  });
  const { data: stats } = trpc.user.stats.useQuery();

  const invalidate = () => {
    utils.user.list.invalidate();
    utils.user.stats.invalidate();
  };

  const createMutation = trpc.user.create.useMutation({
    onSuccess: () => {
      invalidate();
      setModalOpen(false);
      setForm(emptyUser);
    },
    onError: (e) => setError(e.message),
  });
  const roleMutation = trpc.user.updateRole.useMutation({
    onSuccess: invalidate,
  });
  const removeMutation = trpc.user.remove.useMutation({
    onSuccess: () => {
      invalidate();
      setDeleteConfirm(null);
    },
  });

  const statCards = [
    { label: "Membros", value: stats?.total ?? 0, icon: Users, color: "#F97316" },
    {
      label: "Administradores",
      value: stats?.admins ?? 0,
      icon: ShieldCheck,
      color: "#3B82F6",
    },
    {
      label: "Ativos (30 dias)",
      value: stats?.active ?? 0,
      icon: Activity,
      color: "#22C55E",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {statCards.map((s) => (
          <div
            key={s.label}
            className="bg-[#111111] border border-[#27272A] rounded-lg p-4 flex items-center gap-4"
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: `${s.color}1A` }}
            >
              <s.icon className="w-5 h-5" style={{ color: s.color }} />
            </div>
            <div>
              <p className="text-2xl font-semibold text-[#F8FAFC]">{s.value}</p>
              <p className="text-xs text-[#64748B]">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nome ou e-mail..."
            className="pl-9 bg-[#111111] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
          />
        </div>
        {isAdmin && (
          <button
            onClick={() => {
              setForm(emptyUser);
              setError(null);
              setModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors"
          >
            <Plus className="w-4 h-4" />
            Novo Usuário
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#1A1A1A] border-b border-[#27272A]">
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Usuário
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Papel
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden md:table-cell">
                  Último acesso
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden lg:table-cell">
                  Desde
                </th>
                {isAdmin && (
                  <th className="text-right px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                    Ações
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]/50">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={isAdmin ? 5 : 4} className="px-4 py-4">
                      <div className="h-8 bg-[#1A1A1A] rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : members && members.length > 0 ? (
                members.map((m) => {
                  const isSelf = m.id === user?.id;
                  return (
                    <tr
                      key={m.id}
                      className="hover:bg-[#1A1A1A]/50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-[#F97316]/15 flex items-center justify-center text-xs font-medium text-[#F97316] shrink-0">
                            {initials(m.name)}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm text-[#F8FAFC] truncate flex items-center gap-2">
                              {m.name ?? "-"}
                              {isSelf && (
                                <span className="text-[10px] text-[#64748B] border border-[#27272A] rounded px-1">
                                  você
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-[#64748B] truncate">
                              {m.email ?? "-"}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {isAdmin && !isSelf ? (
                          <Select
                            value={m.role}
                            onValueChange={(v) =>
                              roleMutation.mutate({
                                id: m.id,
                                role: v as "user" | "admin",
                              })
                            }
                          >
                            <SelectTrigger className="h-7 w-28 bg-[#1A1A1A] border-[#27272A] text-xs text-[#F8FAFC]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                              <SelectItem value="admin">Administrador</SelectItem>
                              <SelectItem value="user">Usuário</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <span
                            className={`inline-block px-2 py-0.5 text-[10px] font-medium rounded-full ${
                              m.role === "admin"
                                ? "bg-blue-500/10 text-blue-400"
                                : "bg-slate-500/10 text-slate-300"
                            }`}
                          >
                            {m.role === "admin" ? "Administrador" : "Usuário"}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#94A3B8] hidden md:table-cell">
                        {formatDate(m.lastSignInAt)}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#64748B] hidden lg:table-cell">
                        {formatDate(m.createdAt)}
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setDeleteConfirm(m.id)}
                            disabled={isSelf}
                            className="p-1.5 text-[#64748B] hover:text-[#EF4444] hover:bg-[#EF4444]/10 rounded transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-[#64748B]"
                            title={
                              isSelf
                                ? "Você não pode excluir a própria conta"
                                : "Excluir usuário"
                            }
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={isAdmin ? 5 : 4}
                    className="px-4 py-12 text-center text-[#64748B]"
                  >
                    <Users className="w-10 h-10 mx-auto mb-3 text-[#27272A]" />
                    <p className="text-sm">Nenhum usuário encontrado</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              Novo Usuário
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              createMutation.mutate(form);
            }}
            className="space-y-4 mt-2"
          >
            <div>
              <Label className="text-sm text-[#94A3B8]">Nome</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">E-mail</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm text-[#94A3B8]">Senha</Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  minLength={6}
                  required
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Papel</Label>
                <Select
                  value={form.role}
                  onValueChange={(v) =>
                    setForm({ ...form, role: v as "user" | "admin" })
                  }
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="user">Usuário</SelectItem>
                    <SelectItem value="admin">Administrador</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {error && (
              <p className="text-sm text-[#EF4444] bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 text-sm text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-md transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
              >
                {createMutation.isPending && (
                  <Loader2 className="w-4 h-4 animate-spin" />
                )}
                Criar
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              Confirmar Exclusão
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-[#94A3B8] mt-2">
            Tem certeza que deseja excluir este usuário? Esta ação não pode ser
            desfeita.
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <button
              onClick={() => setDeleteConfirm(null)}
              className="px-4 py-2 text-sm text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-md transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={() =>
                deleteConfirm && removeMutation.mutate({ id: deleteConfirm })
              }
              disabled={removeMutation.isPending}
              className="px-4 py-2 bg-[#EF4444] hover:bg-[#DC2626] text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
            >
              {removeMutation.isPending ? "Excluindo..." : "Excluir"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
