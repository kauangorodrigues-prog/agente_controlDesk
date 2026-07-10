import { useMemo, useState } from "react";
import { trpc } from "@/providers/trpc";
import {
  BookOpen,
  Search,
  Plus,
  Pencil,
  Trash2,
  Eye,
  Tag,
  ArrowLeft,
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

const CATEGORY_LABELS: Record<string, string> = {
  procedimentos: "Procedimentos",
  hardware: "Hardware",
  software: "Software",
  rede: "Rede",
  seguranca: "Segurança",
  acesso: "Acesso",
  geral: "Geral",
};

const CATEGORY_COLORS: Record<string, string> = {
  procedimentos: "bg-blue-500/10 text-blue-400",
  hardware: "bg-purple-500/10 text-purple-400",
  software: "bg-green-500/10 text-green-400",
  rede: "bg-cyan-500/10 text-cyan-400",
  seguranca: "bg-red-500/10 text-red-400",
  acesso: "bg-yellow-500/10 text-yellow-400",
  geral: "bg-slate-500/10 text-slate-300",
};

type Category =
  | "procedimentos"
  | "hardware"
  | "software"
  | "rede"
  | "seguranca"
  | "acesso"
  | "geral";

const CATEGORY_OPTIONS = Object.keys(CATEGORY_LABELS) as Category[];

type ArticleForm = {
  title: string;
  summary: string;
  content: string;
  category: Category;
  tags: string;
  status: "draft" | "published";
};

const emptyForm: ArticleForm = {
  title: "",
  summary: "",
  content: "",
  category: "geral",
  tags: "",
  status: "published",
};

/** Minimal, safe markdown renderer (headings, code blocks, bold, lists). */
function ArticleContent({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: React.ReactNode[] = [];
  let code: string[] | null = null;

  const inline = (text: string) =>
    text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={i} className="text-[#F8FAFC] font-semibold">
          {part.slice(2, -2)}
        </strong>
      ) : (
        <span key={i}>{part}</span>
      ),
    );

  lines.forEach((line, idx) => {
    if (line.trim().startsWith("```")) {
      if (code) {
        blocks.push(
          <pre
            key={`c${idx}`}
            className="bg-[#0A0A0A] border border-[#27272A] rounded-lg p-3 my-2 overflow-x-auto text-xs text-[#94A3B8] font-mono"
          >
            {code.join("\n")}
          </pre>,
        );
        code = null;
      } else {
        code = [];
      }
      return;
    }
    if (code) {
      code.push(line);
      return;
    }
    if (line.startsWith("## ")) {
      blocks.push(
        <h3 key={idx} className="text-base font-semibold text-[#F8FAFC] mt-4 mb-1">
          {inline(line.slice(3))}
        </h3>,
      );
    } else if (/^\s*\d+\.\s/.test(line)) {
      blocks.push(
        <p key={idx} className="text-sm text-[#CBD5E1] pl-3">
          {inline(line)}
        </p>,
      );
    } else if (/^\s*[-*]\s/.test(line)) {
      blocks.push(
        <p key={idx} className="text-sm text-[#CBD5E1] pl-3">
          •{inline(line.replace(/^\s*[-*]\s/, " "))}
        </p>,
      );
    } else if (line.trim() === "") {
      blocks.push(<div key={idx} className="h-2" />);
    } else {
      blocks.push(
        <p key={idx} className="text-sm text-[#CBD5E1] leading-relaxed">
          {inline(line)}
        </p>,
      );
    }
  });

  return <div>{blocks}</div>;
}

export default function BaseConhecimento() {
  const utils = trpc.useUtils();

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [readId, setReadId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<ArticleForm>(emptyForm);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const { data: articles, isLoading } = trpc.kb.list.useQuery({
    search: search || undefined,
    category,
    status: "all",
  });
  const { data: categories } = trpc.kb.categories.useQuery();
  const { data: readArticle } = trpc.kb.getById.useQuery(
    { id: readId ?? 0, track: true },
    { enabled: readId !== null },
  );

  const totalCount = useMemo(
    () => (categories ?? []).reduce((acc, c) => acc + c.count, 0),
    [categories],
  );

  const invalidate = () => {
    utils.kb.list.invalidate();
    utils.kb.categories.invalidate();
  };

  const createMutation = trpc.kb.create.useMutation({
    onSuccess: () => {
      invalidate();
      closeModal();
    },
  });
  const updateMutation = trpc.kb.update.useMutation({
    onSuccess: () => {
      invalidate();
      utils.kb.getById.invalidate();
      closeModal();
    },
  });
  const deleteMutation = trpc.kb.delete.useMutation({
    onSuccess: () => {
      invalidate();
      setDeleteConfirm(null);
      setReadId(null);
    },
  });

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (a: NonNullable<typeof articles>[number]) => {
    setEditId(a.id);
    setForm({
      title: a.title,
      summary: a.summary ?? "",
      content: a.content,
      category: a.category,
      tags: a.tags ?? "",
      status: a.status,
    });
    setReadId(null);
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
      summary: form.summary || undefined,
      tags: form.tags || undefined,
    };
    if (editId) {
      updateMutation.mutate({ id: editId, ...payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[#94A3B8] text-sm">
          <BookOpen className="w-4 h-4 text-[#F97316]" />
          <span>
            {totalCount} artigo{totalCount === 1 ? "" : "s"} publicado
            {totalCount === 1 ? "" : "s"}
          </span>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-[#F97316] hover:bg-[#EA580C] text-white text-sm font-medium rounded-md transition-colors"
        >
          <Plus className="w-4 h-4" />
          Novo Artigo
        </button>
      </div>

      {/* Search + categories */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar na base de conhecimento..."
            className="pl-9 bg-[#111111] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <CategoryChip
            active={category === "all"}
            label="Todas"
            count={totalCount}
            onClick={() => setCategory("all")}
          />
          {CATEGORY_OPTIONS.map((key) => {
            const c = categories?.find((x) => x.category === key);
            if (!c) return null;
            return (
              <CategoryChip
                key={key}
                active={category === key}
                label={CATEGORY_LABELS[key]}
                count={c.count}
                onClick={() => setCategory(key)}
              />
            );
          })}
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-40 bg-[#111111] border border-[#27272A] rounded-lg animate-pulse"
            />
          ))}
        </div>
      ) : articles && articles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {articles.map((a) => (
            <div
              key={a.id}
              onClick={() => setReadId(a.id)}
              className="group bg-[#111111] border border-[#27272A] rounded-lg p-4 hover:border-[#F97316]/50 transition-colors cursor-pointer flex flex-col"
            >
              <div className="flex items-center justify-between mb-2">
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                    CATEGORY_COLORS[a.category] ?? CATEGORY_COLORS.geral
                  }`}
                >
                  {CATEGORY_LABELS[a.category] ?? a.category}
                </span>
                {a.status === "draft" && (
                  <span className="text-[10px] text-[#64748B] border border-[#27272A] rounded px-1.5 py-0.5">
                    Rascunho
                  </span>
                )}
              </div>
              <h3 className="text-sm font-semibold text-[#F8FAFC] line-clamp-2 group-hover:text-[#F97316] transition-colors">
                {a.title}
              </h3>
              {a.summary && (
                <p className="text-xs text-[#94A3B8] mt-1.5 line-clamp-3 flex-1">
                  {a.summary}
                </p>
              )}
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#27272A]/60">
                <span className="flex items-center gap-1 text-[11px] text-[#64748B]">
                  <Eye className="w-3 h-3" />
                  {a.views}
                </span>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openEdit(a);
                    }}
                    className="p-1 text-[#64748B] hover:text-[#F97316] transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirm(a.id);
                    }}
                    className="p-1 text-[#64748B] hover:text-[#EF4444] transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 text-[#64748B]">
          <BookOpen className="w-12 h-12 mx-auto mb-3 text-[#27272A]" />
          <p className="text-sm">Nenhum artigo encontrado</p>
        </div>
      )}

      {/* Read dialog */}
      <Dialog open={readId !== null} onOpenChange={(o) => !o && setReadId(null)}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-2xl max-h-[85vh] overflow-y-auto">
          {readArticle ? (
            <>
              <DialogHeader>
                <button
                  onClick={() => setReadId(null)}
                  className="flex items-center gap-1 text-xs text-[#64748B] hover:text-[#94A3B8] w-fit mb-2"
                >
                  <ArrowLeft className="w-3 h-3" /> Voltar
                </button>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      CATEGORY_COLORS[readArticle.category] ??
                      CATEGORY_COLORS.geral
                    }`}
                  >
                    {CATEGORY_LABELS[readArticle.category] ??
                      readArticle.category}
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-[#64748B]">
                    <Eye className="w-3 h-3" />
                    {readArticle.views}
                  </span>
                </div>
                <DialogTitle className="text-xl font-semibold">
                  {readArticle.title}
                </DialogTitle>
                {readArticle.summary && (
                  <p className="text-sm text-[#94A3B8] mt-1">
                    {readArticle.summary}
                  </p>
                )}
              </DialogHeader>
              <div className="mt-2">
                <ArticleContent content={readArticle.content} />
              </div>
              {readArticle.tags && (
                <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-[#27272A]">
                  <Tag className="w-3.5 h-3.5 text-[#64748B]" />
                  {readArticle.tags.split(",").map((t) => (
                    <span
                      key={t}
                      className="text-[11px] text-[#94A3B8] bg-[#1A1A1A] rounded px-2 py-0.5"
                    >
                      {t.trim()}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between mt-4 text-xs text-[#64748B]">
                <span>Por {readArticle.authorName ?? "Equipe"}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => openEdit(readArticle)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[#94A3B8] hover:text-[#F97316] hover:bg-[#F97316]/10 rounded transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" /> Editar
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(readArticle.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-[#94A3B8] hover:text-[#EF4444] hover:bg-[#EF4444]/10 rounded transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Excluir
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="h-40 flex items-center justify-center text-[#64748B]">
              Carregando...
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create/Edit dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#111111] border-[#27272A] text-[#F8FAFC] max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">
              {editId ? "Editar Artigo" : "Novo Artigo"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div>
              <Label className="text-sm text-[#94A3B8]">Título</Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Título do artigo"
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">Resumo</Label>
              <Input
                value={form.summary}
                onChange={(e) => setForm({ ...form, summary: e.target.value })}
                placeholder="Breve descrição (opcional)"
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm text-[#94A3B8]">Categoria</Label>
                <Select
                  value={form.category}
                  onValueChange={(v) =>
                    setForm({ ...form, category: v as Category })
                  }
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    {CATEGORY_OPTIONS.map((key) => (
                      <SelectItem key={key} value={key}>
                        {CATEGORY_LABELS[key]}
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
                    setForm({ ...form, status: v as ArticleForm["status"] })
                  }
                >
                  <SelectTrigger className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1A1A] border-[#27272A]">
                    <SelectItem value="published">Publicado</SelectItem>
                    <SelectItem value="draft">Rascunho</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">
                Tags (separadas por vírgula)
              </Label>
              <Input
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="rede, vpn, acesso"
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316]"
              />
            </div>
            <div>
              <Label className="text-sm text-[#94A3B8]">
                Conteúdo (suporta Markdown básico)
              </Label>
              <Textarea
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                placeholder={"## Título\n\nTexto do artigo com **destaque**..."}
                rows={10}
                required
                className="mt-1 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#F97316] font-mono text-xs"
              />
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
                    : "Publicar"}
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
            Tem certeza que deseja excluir este artigo? Esta ação não pode ser
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

function CategoryChip({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${
        active
          ? "bg-[#F97316] text-white border-[#F97316]"
          : "bg-[#111111] text-[#94A3B8] border-[#27272A] hover:text-[#F8FAFC] hover:border-[#3F3F46]"
      }`}
    >
      {label}
      <span
        className={`text-[10px] ${active ? "text-white/80" : "text-[#64748B]"}`}
      >
        {count}
      </span>
    </button>
  );
}
