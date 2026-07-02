import { useState } from "react";
import { trpc } from "@/providers/trpc";
import type { Ticket as TicketRow } from "@db/schema";
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Ticket,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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

const STATUS_LABELS: Record<string, string> = {
  open: "Aberto",
  in_progress: "Em Andamento",
  pending: "Pendente",
  resolved: "Resolvido",
  closed: "Fechado",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

const CATEGORY_LABELS: Record<string, string> = {
  hardware: "Hardware",
  software: "Software",
  network: "Rede",
  security: "Seguranca",
  access: "Acesso",
  other: "Outro",
};

type TicketForm = {
  title: string;
  description: string;
  category: "hardware" | "software" | "network" | "security" | "access" | "other";
  priority: "low" | "medium" | "high" | "critical";
  status: "open" | "in_progress" | "pending" | "resolved" | "closed";
  requesterName: string;
  requesterEmail: string;
};

const emptyForm: TicketForm = {
  title: "",
  description: "",
  category: "other",
  priority: "medium",
  status: "open",
  requesterName: "",
  requesterEmail: "",
};

export default function Tickets() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<TicketForm>(emptyForm);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const utils = trpc.useUtils();

  const { data, isLoading } = trpc.ticket.list.useQuery({
    search: search || undefined,
    status: statusFilter,
    priority: priorityFilter,
    page,
    limit: 10,
  });

  const createMutation = trpc.ticket.create.useMutation({
    onSuccess: () => {
      utils.ticket.list.invalidate();
      utils.dashboard.stats.invalidate();
      utils.dashboard.recentTickets.invalidate();
      closeModal();
    },
  });

  const updateMutation = trpc.ticket.update.useMutation({
    onSuccess: () => {
      utils.ticket.list.invalidate();
      utils.dashboard.stats.invalidate();
      utils.dashboard.recentTickets.invalidate();
      closeModal();
    },
  });

  const deleteMutation = trpc.ticket.delete.useMutation({
    onSuccess: () => {
      utils.ticket.list.invalidate();
      utils.dashboard.stats.invalidate();
      utils.dashboard.recentTickets.invalidate();
      setDeleteConfirm(null);
    },
  });

  const openCreateModal = () => {
    setEditId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEditModal = (ticket: TicketRow) => {
    setEditId(ticket.id);
    setForm({
      title: ticket.title,
      description: ticket.description ?? "",
      category: ticket.category,
      priority: ticket.priority,
      status: ticket.status,
      requesterName: ticket.requesterName ?? "",
      requesterEmail: ticket.requesterEmail ?? "",
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
    if (editId) {
      updateMutation.mutate({ id: editId, ...form });
    } else {
      createMutation.mutate(form);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      open: "bg-orange-500/10 text-orange-400 border-orange-500/20",
      in_progress: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      resolved: "bg-green-500/10 text-green-400 border-green-500/20",
      closed: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    };
    return colors[status] ?? colors.open;
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: "text-green-400",
      medium: "text-yellow-400",
      high: "text-orange-400",
      critical: "text-red-400",
    };
    const dots: Record<string, string> = {
      low: "bg-green-400",
      medium: "bg-yellow-400",
      high: "bg-orange-400",
      critical: "bg-red-400",
    };
    return { text: colors[priority] ?? colors.medium, dot: dots[priority] ?? dots.medium };
  };

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <Input
            placeholder="Buscar tickets..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-10 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316] focus:ring-[#F97316]/20"
          />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
            <SelectTrigger className="w-[140px] bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
              <Filter className="w-4 h-4 mr-2 text-[#64748B]" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="open">Aberto</SelectItem>
              <SelectItem value="in_progress">Em Andamento</SelectItem>
              <SelectItem value="pending">Pendente</SelectItem>
              <SelectItem value="resolved">Resolvido</SelectItem>
              <SelectItem value="closed">Fechado</SelectItem>
            </SelectContent>
          </Select>

          <Select value={priorityFilter} onValueChange={(v) => { setPriorityFilter(v); setPage(1); }}>
            <SelectTrigger className="w-[140px] bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
              <SelectValue placeholder="Prioridade" />
            </SelectTrigger>
            <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
              <SelectItem value="all">Todas</SelectItem>
              <SelectItem value="low">Baixa</SelectItem>
              <SelectItem value="medium">Média</SelectItem>
              <SelectItem value="high">Alta</SelectItem>
              <SelectItem value="critical">Crítica</SelectItem>
            </SelectContent>
          </Select>

          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors orange-glow"
          >
            <Plus className="w-4 h-4" />
            Novo Ticket
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#1A1A1A] border-b border-[#27272A]">
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">ID</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Título</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Categoria</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Prioridade</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Data</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]/50">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={7} className="px-4 py-4">
                      <div className="h-8 bg-[#1A1A1A] rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-[#64748B]">
                    <Ticket className="w-10 h-10 mx-auto mb-3 text-[#27272A]" />
                    <p className="text-sm">Nenhum ticket encontrado</p>
                  </td>
                </tr>
              ) : (
                data?.items.map((ticket) => {
                  const priorityStyle = getPriorityBadge(ticket.priority);
                  return (
                    <tr key={ticket.id} className="hover:bg-[#1A1A1A]/50 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-[#64748B]">#{ticket.id}</td>
                      <td className="px-4 py-3 text-sm text-[#F8FAFC] max-w-[300px] truncate">{ticket.title}</td>
                      <td className="px-4 py-3 text-sm text-[#94A3B8]">{CATEGORY_LABELS[ticket.category] ?? ticket.category}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 text-[10px] font-medium rounded-full border ${getStatusBadge(ticket.status)}`}>
                          {STATUS_LABELS[ticket.status] ?? ticket.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`flex items-center gap-1.5 text-xs font-medium ${priorityStyle.text}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${priorityStyle.dot}`} />
                          {PRIORITY_LABELS[ticket.priority] ?? ticket.priority}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-[#64748B]">
                        {ticket.createdAt ? new Date(ticket.createdAt).toLocaleDateString("pt-BR") : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openEditModal(ticket)}
                            className="p-1.5 text-[#64748B] hover:text-[#F97316] hover:bg-[#F97316]/10 rounded transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(ticket.id)}
                            className="p-1.5 text-[#64748B] hover:text-[#EF4444] hover:bg-[#EF4444]/10 rounded transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-[#27272A]">
            <p className="text-xs text-[#64748B]">
              {data.total} tickets · Página {data.page} de {data.totalPages}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 text-[#64748B] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
                disabled={page === data.totalPages}
                className="p-1.5 text-[#64748B] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              {editId ? "Editar Ticket" : "Novo Ticket"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div>
              <Label className="text-sm text-[#94A3B8]">Título</Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Descreva o problema"
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316] focus:ring-[#F97316]/20"
              />
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">Descrição</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Detalhes adicionais..."
                rows={3}
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316] focus:ring-[#F97316]/20"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm text-[#94A3B8]">Categoria</Label>
                <Select value={form.category} onValueChange={(v: TicketForm["category"]) => setForm({ ...form, category: v })}>
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="hardware">Hardware</SelectItem>
                    <SelectItem value="software">Software</SelectItem>
                    <SelectItem value="network">Rede</SelectItem>
                    <SelectItem value="security">Seguranca</SelectItem>
                    <SelectItem value="access">Acesso</SelectItem>
                    <SelectItem value="other">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Prioridade</Label>
                <Select value={form.priority} onValueChange={(v: TicketForm["priority"]) => setForm({ ...form, priority: v })}>
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="low">Baixa</SelectItem>
                    <SelectItem value="medium">Média</SelectItem>
                    <SelectItem value="high">Alta</SelectItem>
                    <SelectItem value="critical">Critica</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {editId && (
              <div>
                <Label className="text-sm text-[#94A3B8]">Status</Label>
                <Select value={form.status} onValueChange={(v: TicketForm["status"]) => setForm({ ...form, status: v })}>
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="open">Aberto</SelectItem>
                    <SelectItem value="in_progress">Em Andamento</SelectItem>
                    <SelectItem value="pending">Pendente</SelectItem>
                    <SelectItem value="resolved">Resolvido</SelectItem>
                    <SelectItem value="closed">Fechado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm text-[#94A3B8]">Solicitante</Label>
                <Input
                  value={form.requesterName}
                  onChange={(e) => setForm({ ...form, requesterName: e.target.value })}
                  placeholder="Nome"
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Email</Label>
                <Input
                  value={form.requesterEmail}
                  onChange={(e) => setForm({ ...form, requesterEmail: e.target.value })}
                  placeholder="email@empresa.com"
                  type="email"
                  className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
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
                {createMutation.isPending || updateMutation.isPending ? "Salvando..." : editId ? "Salvar" : "Criar"}
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">Confirmar Exclusão</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-[#94A3B8] mt-2">
            Tem certeza que deseja excluir este ticket? Esta ação não pode ser desfeita.
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <button
              onClick={() => setDeleteConfirm(null)}
              className="px-4 py-2 text-sm text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-md transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={() => deleteConfirm && deleteMutation.mutate({ id: deleteConfirm })}
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
