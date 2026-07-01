import { useState } from "react";
import { trpc } from "@/providers/trpc";
import type { Incident } from "@db/schema";
import {
  Plus,
  AlertTriangle,
  LayoutGrid,
  List,
  Pencil,
  Trash2,
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const STATUS_COLUMNS = [
  { key: "open", label: "Aberto", color: "#F97316" },
  { key: "in_progress", label: "Em Andamento", color: "#3B82F6" },
  { key: "pending", label: "Pendente", color: "#EAB308" },
  { key: "resolved", label: "Resolvido", color: "#22C55E" },
];

const PRIORITY_COLORS: Record<string, string> = {
  low: "#22C55E",
  medium: "#EAB308",
  high: "#F97316",
  critical: "#EF4444",
};

const IMPACT_LABELS: Record<string, string> = {
  individual: "Individual",
  team: "Equipe",
  department: "Departamento",
  company: "Empresa",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

type IncidentForm = {
  title: string;
  description: string;
  priority: "low" | "medium" | "high" | "critical";
  impact: "individual" | "team" | "department" | "company";
  status: "open" | "in_progress" | "pending" | "resolved";
};

const emptyForm: IncidentForm = {
  title: "",
  description: "",
  priority: "medium",
  impact: "individual",
  status: "open",
};

export default function Incidentes() {
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<IncidentForm>(emptyForm);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const utils = trpc.useUtils();

  const { data: incidents, isLoading } = trpc.incident.list.useQuery({
    status: "all",
  });

  const createMutation = trpc.incident.create.useMutation({
    onSuccess: () => {
      utils.incident.list.invalidate();
      utils.dashboard.stats.invalidate();
      closeModal();
    },
  });

  const updateMutation = trpc.incident.update.useMutation({
    onSuccess: () => {
      utils.incident.list.invalidate();
      utils.dashboard.stats.invalidate();
      closeModal();
    },
  });

  const deleteMutation = trpc.incident.delete.useMutation({
    onSuccess: () => {
      utils.incident.list.invalidate();
      utils.dashboard.stats.invalidate();
      setDeleteConfirm(null);
    },
  });

  const openCreateModal = () => {
    setEditId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEditModal = (incident: Incident) => {
    setEditId(incident.id);
    setForm({
      title: incident.title,
      description: incident.description ?? "",
      priority: incident.priority,
      impact: incident.impact,
      status: incident.status,
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

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: "bg-green-500/10 text-green-400",
      medium: "bg-yellow-500/10 text-yellow-400",
      high: "bg-orange-500/10 text-orange-400",
      critical: "bg-red-500/10 text-red-400",
    };
    return colors[priority] ?? colors.medium;
  };

  const getImpactBadge = (impact: string) => {
    const colors: Record<string, string> = {
      individual: "text-[#94A3B8]",
      team: "text-[#EAB308]",
      department: "text-[#F97316]",
      company: "text-[#EF4444]",
    };
    return colors[impact] ?? colors.individual;
  };

  const incidentsByStatus = (status: string) =>
    (incidents ?? []).filter((i) => i.status === status);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <Tabs value={view} onValueChange={(v) => setView(v as "kanban" | "list")}>
          <TabsList className="bg-[#111111] border border-[#27272A]">
            <TabsTrigger
              value="kanban"
              className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8]"
            >
              <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
              Kanban
            </TabsTrigger>
            <TabsTrigger
              value="list"
              className="data-[state=active]:bg-[#F97316] data-[state=active]:text-white text-[#94A3B8]"
            >
              <List className="w-3.5 h-3.5 mr-1.5" />
              Lista
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors orange-glow"
        >
          <Plus className="w-4 h-4" />
          Novo Incidente
        </button>
      </div>

      {/* Kanban View */}
      {view === "kanban" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {STATUS_COLUMNS.map((column) => {
            const columnIncidents = incidentsByStatus(column.key);
            return (
              <div key={column.key} className="bg-[#111111] border border-[#27272A] rounded-lg flex flex-col">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#27272A]">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: column.color }} />
                    <span className="text-sm font-medium text-[#F8FAFC]">{column.label}</span>
                  </div>
                  <span className="text-xs text-[#64748B] bg-[#0A0A0A] px-2 py-0.5 rounded-full">
                    {columnIncidents.length}
                  </span>
                </div>
                <div className="flex-1 p-3 space-y-3 min-h-[200px] max-h-[calc(100vh-280px)] overflow-y-auto">
                  {columnIncidents.map((incident) => (
                    <div
                      key={incident.id}
                      className="bg-[#0A0A0A] rounded-lg p-3 hover:bg-[#1A1A1A] transition-colors cursor-pointer group"
                      onClick={() => openEditModal(incident)}
                    >
                      <div className="flex items-start gap-2 mb-2">
                        <div
                          className="w-1 h-full min-h-[40px] rounded-full shrink-0"
                          style={{ backgroundColor: PRIORITY_COLORS[incident.priority] }}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[#F8FAFC] line-clamp-2">{incident.title}</p>
                          <p className="text-xs text-[#64748B] mt-1">#{incident.id}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${getPriorityBadge(
                              incident.priority
                            )}`}
                          >
                            {PRIORITY_LABELS[incident.priority]}
                          </span>
                          <span className={`text-[10px] ${getImpactBadge(incident.impact)}`}>
                            {IMPACT_LABELS[incident.impact]}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditModal(incident);
                            }}
                            className="p-1 text-[#64748B] hover:text-[#F97316] transition-colors"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteConfirm(incident.id);
                            }}
                            className="p-1 text-[#64748B] hover:text-[#EF4444] transition-colors"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}

                  {columnIncidents.length === 0 && (
                    <div className="text-center py-8 text-[#64748B]">
                      <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-30" />
                      <p className="text-xs">Nenhum incidente</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* List View */
        <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-[#1A1A1A] border-b border-[#27272A]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">ID</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">Título</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">Prioridade</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">Impacto</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">Data</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">Ações</th>
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
                ) : incidents?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-[#64748B]">
                      <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-[#27272A]" />
                      <p className="text-sm">Nenhum incidente encontrado</p>
                    </td>
                  </tr>
                ) : (
                  incidents?.map((incident) => (
                    <tr key={incident.id} className="hover:bg-[#1A1A1A]/50 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-[#64748B]">#{incident.id}</td>
                      <td className="px-4 py-3 text-sm text-[#F8FAFC] max-w-[300px] truncate">{incident.title}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 text-[10px] font-medium rounded-full ${getPriorityBadge(incident.priority)}`}>
                          {PRIORITY_LABELS[incident.priority]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#94A3B8]">{IMPACT_LABELS[incident.impact]}</td>
                      <td className="px-4 py-3 text-xs text-[#64748B]">
                        {incident.createdAt ? new Date(incident.createdAt).toLocaleDateString("pt-BR") : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openEditModal(incident)}
                            className="p-1.5 text-[#64748B] hover:text-[#F97316] hover:bg-[#F97316]/10 rounded transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(incident.id)}
                            className="p-1.5 text-[#64748B] hover:text-[#EF4444] hover:bg-[#EF4444]/10 rounded transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              {editId ? "Editar Incidente" : "Novo Incidente"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div>
              <Label className="text-sm text-[#94A3B8]">Título</Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Descreva o incidente"
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">Descrição</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Detalhes do incidente..."
                rows={3}
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-sm text-[#94A3B8]">Prioridade</Label>
                <Select value={form.priority} onValueChange={(v: IncidentForm["priority"]) => setForm({ ...form, priority: v })}>
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
              <div>
                <Label className="text-sm text-[#94A3B8]">Impacto</Label>
                <Select value={form.impact} onValueChange={(v: IncidentForm["impact"]) => setForm({ ...form, impact: v })}>
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="individual">Individual</SelectItem>
                    <SelectItem value="team">Equipe</SelectItem>
                    <SelectItem value="department">Departamento</SelectItem>
                    <SelectItem value="company">Empresa</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm text-[#94A3B8]">Status</Label>
                <Select value={form.status} onValueChange={(v: IncidentForm["status"]) => setForm({ ...form, status: v })}>
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="open">Aberto</SelectItem>
                    <SelectItem value="in_progress">Em Andamento</SelectItem>
                    <SelectItem value="pending">Pendente</SelectItem>
                    <SelectItem value="resolved">Resolvido</SelectItem>
                  </SelectContent>
                </Select>
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
            Tem certeza que deseja excluir este incidente? Esta ação não pode ser desfeita.
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
