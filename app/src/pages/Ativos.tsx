import { useState } from "react";
import { trpc } from "@/providers/trpc";
import {
  HardDrive,
  Plus,
  Pencil,
  Trash2,
  Search,
  Laptop,
  Monitor,
  Server,
  Network,
  Printer,
  Smartphone,
  KeyRound,
  Box,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type AssetType =
  | "notebook"
  | "desktop"
  | "servidor"
  | "monitor"
  | "rede"
  | "impressora"
  | "mobile"
  | "licenca"
  | "outro";
type AssetStatus = "ativo" | "em_manutencao" | "em_estoque" | "aposentado";

const TYPE_LABELS: Record<AssetType, string> = {
  notebook: "Notebook",
  desktop: "Desktop",
  servidor: "Servidor",
  monitor: "Monitor",
  rede: "Rede",
  impressora: "Impressora",
  mobile: "Mobile",
  licenca: "Licença",
  outro: "Outro",
};

const TYPE_ICONS: Record<AssetType, typeof Laptop> = {
  notebook: Laptop,
  desktop: Monitor,
  servidor: Server,
  monitor: Monitor,
  rede: Network,
  impressora: Printer,
  mobile: Smartphone,
  licenca: KeyRound,
  outro: Box,
};

const STATUS_LABELS: Record<AssetStatus, string> = {
  ativo: "Ativo",
  em_manutencao: "Em manutenção",
  em_estoque: "Em estoque",
  aposentado: "Aposentado",
};

const STATUS_BADGE: Record<AssetStatus, string> = {
  ativo: "bg-green-500/10 text-green-400",
  em_manutencao: "bg-orange-500/10 text-orange-400",
  em_estoque: "bg-blue-500/10 text-blue-400",
  aposentado: "bg-slate-500/10 text-slate-300",
};

const TYPE_OPTIONS = Object.keys(TYPE_LABELS) as AssetType[];
const STATUS_OPTIONS = Object.keys(STATUS_LABELS) as AssetStatus[];

type AssetForm = {
  name: string;
  tag: string;
  type: AssetType;
  status: AssetStatus;
  serialNumber: string;
  location: string;
  assignedTo: number | null;
  assignedName: string;
  purchaseDate: string;
  notes: string;
};

const emptyForm: AssetForm = {
  name: "",
  tag: "",
  type: "notebook",
  status: "ativo",
  serialNumber: "",
  location: "",
  assignedTo: null,
  assignedName: "",
  purchaseDate: "",
  notes: "",
};

export default function Ativos() {
  const utils = trpc.useUtils();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<AssetForm>(emptyForm);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const { data: items, isLoading } = trpc.asset.list.useQuery({
    search: search || undefined,
    type: typeFilter,
    status: statusFilter,
  });
  const { data: stats } = trpc.asset.stats.useQuery();
  const { data: team } = trpc.user.list.useQuery(undefined);

  const invalidate = () => {
    utils.asset.list.invalidate();
    utils.asset.stats.invalidate();
  };

  const createMutation = trpc.asset.create.useMutation({
    onSuccess: () => {
      invalidate();
      closeModal();
    },
  });
  const updateMutation = trpc.asset.update.useMutation({
    onSuccess: () => {
      invalidate();
      closeModal();
    },
  });
  const deleteMutation = trpc.asset.delete.useMutation({
    onSuccess: () => {
      invalidate();
      setDeleteConfirm(null);
    },
  });

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (a: NonNullable<typeof items>[number]) => {
    setEditId(a.id);
    setForm({
      name: a.name,
      tag: a.tag ?? "",
      type: a.type,
      status: a.status,
      serialNumber: a.serialNumber ?? "",
      location: a.location ?? "",
      assignedTo: a.assignedTo ?? null,
      assignedName: a.assignedName ?? "",
      purchaseDate: a.purchaseDate ?? "",
      notes: a.notes ?? "",
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditId(null);
    setForm(emptyForm);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      tag: form.tag || undefined,
      serialNumber: form.serialNumber || undefined,
      location: form.location || undefined,
      assignedName: form.assignedName || undefined,
      purchaseDate: form.purchaseDate || undefined,
      notes: form.notes || undefined,
    };
    if (editId) {
      updateMutation.mutate({ id: editId, ...payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const statCards = [
    { label: "Total", value: stats?.total ?? 0, color: "#F97316" },
    { label: "Ativos", value: stats?.ativo ?? 0, color: "#22C55E" },
    { label: "Em manutenção", value: stats?.em_manutencao ?? 0, color: "#F59E0B" },
    { label: "Em estoque", value: stats?.em_estoque ?? 0, color: "#3B82F6" },
  ];

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <div
            key={s.label}
            className="bg-[#111111] border border-[#27272A] rounded-lg p-4"
          >
            <p className="text-2xl font-semibold" style={{ color: s.color }}>
              {s.value}
            </p>
            <p className="text-xs text-[#64748B] mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nome, tag, série, responsável..."
            className="pl-9 bg-[#111111] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
          />
        </div>
        <div className="flex gap-2">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-36 bg-[#111111] border-[#27272A] text-[#F8FAFC]">
              <SelectValue placeholder="Tipo" />
            </SelectTrigger>
            <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
              <SelectItem value="all">Todos os tipos</SelectItem>
              {TYPE_OPTIONS.map((t) => (
                <SelectItem key={t} value={t}>
                  {TYPE_LABELS[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36 bg-[#111111] border-[#27272A] text-[#F8FAFC]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
              <SelectItem value="all">Todos os status</SelectItem>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {STATUS_LABELS[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Novo Ativo
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#1A1A1A] border-b border-[#27272A]">
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Ativo
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden sm:table-cell">
                  Tipo
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden md:table-cell">
                  Responsável
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden lg:table-cell">
                  Localização
                </th>
                <th className="text-right px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]/50">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-4 py-4">
                      <div className="h-8 bg-[#1A1A1A] rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : items && items.length > 0 ? (
                items.map((a) => {
                  const Icon = TYPE_ICONS[a.type] ?? Box;
                  return (
                    <tr
                      key={a.id}
                      className="hover:bg-[#1A1A1A]/50 transition-colors cursor-pointer"
                      onClick={() => openEdit(a)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-[#F97316]/10 flex items-center justify-center shrink-0">
                            <Icon className="w-4 h-4 text-[#F97316]" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm text-[#F8FAFC] truncate">
                              {a.name}
                            </p>
                            <p className="text-xs text-[#64748B] font-mono truncate">
                              {a.tag ?? "—"}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#94A3B8] hidden sm:table-cell">
                        {TYPE_LABELS[a.type]}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 text-[10px] font-medium rounded-full ${STATUS_BADGE[a.status]}`}
                        >
                          {STATUS_LABELS[a.status]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#94A3B8] hidden md:table-cell">
                        {a.assignedName || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#64748B] hidden lg:table-cell">
                        {a.location || "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openEdit(a);
                            }}
                            className="p-1.5 text-[#64748B] hover:text-[#F97316] hover:bg-[#F97316]/10 rounded transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteConfirm(a.id);
                            }}
                            className="p-1.5 text-[#64748B] hover:text-[#EF4444] hover:bg-[#EF4444]/10 rounded transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-[#64748B]">
                    <HardDrive className="w-10 h-10 mx-auto mb-3 text-[#27272A]" />
                    <p className="text-sm">Nenhum ativo encontrado</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create/Edit dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              {editId ? "Editar Ativo" : "Novo Ativo"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Label className="text-sm text-[#94A3B8]">Nome</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Tag / Patrimônio</Label>
                <Input
                  value={form.tag}
                  onChange={(e) => setForm({ ...form, tag: e.target.value })}
                  placeholder="NB-0042"
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Nº de série</Label>
                <Input
                  value={form.serialNumber}
                  onChange={(e) =>
                    setForm({ ...form, serialNumber: e.target.value })
                  }
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Tipo</Label>
                <Select
                  value={form.type}
                  onValueChange={(v) =>
                    setForm({ ...form, type: v as AssetType })
                  }
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    {TYPE_OPTIONS.map((t) => (
                      <SelectItem key={t} value={t}>
                        {TYPE_LABELS[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Status</Label>
                <Select
                  value={form.status}
                  onValueChange={(v) =>
                    setForm({ ...form, status: v as AssetStatus })
                  }
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    {STATUS_OPTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Responsável</Label>
                <Select
                  value={form.assignedTo ? String(form.assignedTo) : "none"}
                  onValueChange={(v) => {
                    if (v === "none") {
                      setForm({ ...form, assignedTo: null, assignedName: "" });
                    } else {
                      const member = team?.find((m) => String(m.id) === v);
                      setForm({
                        ...form,
                        assignedTo: Number(v),
                        assignedName: member?.name ?? "",
                      });
                    }
                  }}
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue placeholder="Ninguém" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="none">Ninguém</SelectItem>
                    {team?.map((m) => (
                      <SelectItem key={m.id} value={String(m.id)}>
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Data de compra</Label>
                <Input
                  type="date"
                  value={form.purchaseDate}
                  onChange={(e) =>
                    setForm({ ...form, purchaseDate: e.target.value })
                  }
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] focus:border-[#F97316]"
                />
              </div>
              <div className="col-span-2">
                <Label className="text-sm text-[#94A3B8]">Localização</Label>
                <Input
                  value={form.location}
                  onChange={(e) =>
                    setForm({ ...form, location: e.target.value })
                  }
                  placeholder="Matriz - 3º andar"
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div className="col-span-2">
                <Label className="text-sm text-[#94A3B8]">Observações</Label>
                <Textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={2}
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={closeModal}
                className="px-4 py-2 text-sm text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-md transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? "Salvando..."
                  : editId
                    ? "Salvar"
                    : "Criar"}
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
            Tem certeza que deseja excluir este ativo? Esta ação não pode ser
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
                deleteConfirm && deleteMutation.mutate({ id: deleteConfirm })
              }
              disabled={deleteMutation.isPending}
              className="px-4 py-2 bg-[#EF4444] hover:bg-[#DC2626] text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50"
            >
              {deleteMutation.isPending ? "Excluindo..." : "Excluir"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
