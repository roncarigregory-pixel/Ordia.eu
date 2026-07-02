import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { StatusBadge } from "@/components/StatusBadge";
import { ProductSearch } from "@/components/ProductSearch";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  ArrowLeft, CheckCircle2, Trash2, Copy, Plus, Download, AlertTriangle,
  FileText, GripVertical, Sparkles, History, ChevronDown, ImageIcon, Mail, MessageSquare, UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

function confColor(c) {
  if (c >= 0.8) return "text-emerald-600";
  if (c >= 0.5) return "text-amber-600";
  return "text-red-600";
}

function tokens(s) {
  return (s || "").toLowerCase().replace(/[^a-zà-ù0-9\s]/gi, " ").split(/\s+/).filter((w) => w.length > 2);
}

function suggestProducts(raw, products) {
  const t = tokens(raw);
  if (!t.length) return [];
  const scored = products.map((p) => {
    const hay = `${p.name} ${(p.aliases || []).join(" ")}`.toLowerCase();
    const score = t.reduce((s, tok) => s + (hay.includes(tok) ? 1 : 0), 0);
    return { p, score };
  }).filter((x) => x.score > 0).sort((a, b) => b.score - a.score);
  return scored.slice(0, 3).map((x) => x.p);
}

function SortableRow({ it, products, onMatch, onUpdate, onDuplicate, onRemove, onCreate }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: it.id });
  const style = { transform: CSS.Transform.toString(transform), transition, zIndex: isDragging ? 20 : "auto" };
  const suggestions = !it.matched_product_id ? suggestProducts(it.raw_text, products) : [];

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid={`line-item-${it.id}`}
      className={cn(
        "rounded-xl border bg-white p-3.5 transition-colors",
        isDragging && "shadow-lg",
        it.needs_review ? "border-amber-200" : "border-border hover:border-slate-300"
      )}
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes} {...listeners}
          data-testid={`drag-item-${it.id}`}
          className="mt-1 cursor-grab touch-none text-slate-300 hover:text-slate-500 active:cursor-grabbing"
        >
          <GripVertical size={16} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <p className="flex-1 truncate font-mono text-xs text-muted-foreground" title={it.raw_text}>
              “{it.raw_text || "riga manuale"}”
            </p>
            <div className="flex shrink-0 items-center gap-2">
              <span className={cn("font-mono text-xs font-semibold", confColor(it.confidence))}>
                {Math.round((it.confidence || 0) * 100)}%
              </span>
              {it.learned && (
                <span title="Appreso da correzioni precedenti" className="flex items-center gap-1 rounded-full bg-ai-soft px-1.5 py-0.5 text-[10px] font-medium text-ai">
                  <Sparkles size={10} /> appreso
                </span>
              )}
              <button data-testid={`duplicate-item-${it.id}`} onClick={() => onDuplicate(it.id)} className="text-slate-300 transition-colors hover:text-primary" title="Duplica">
                <Copy size={15} />
              </button>
              <button data-testid={`remove-item-${it.id}`} onClick={() => onRemove(it.id)} className="text-slate-300 transition-colors hover:text-red-500" title="Elimina">
                <Trash2 size={15} />
              </button>
            </div>
          </div>

          <div className="mt-2.5 grid grid-cols-12 items-center gap-2">
            <div className="col-span-7">
              <ProductSearch
                products={products}
                value={it.matched_product_id}
                invalid={!it.matched_product_id}
                testid={`match-select-${it.id}`}
                onSelect={(pid) => onMatch(it.id, pid)}
                onCreate={(name) => onCreate(it.id, name)}
              />
            </div>
            <input
              data-testid={`qty-input-${it.id}`}
              type="number" min="0" step="0.5" value={it.quantity}
              onChange={(e) => onUpdate(it.id, { quantity: parseFloat(e.target.value) || 0 })}
              className="col-span-2 rounded-lg border border-input bg-white px-2 py-2 text-center font-mono text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <input
              data-testid={`unit-input-${it.id}`}
              value={it.unit}
              onChange={(e) => onUpdate(it.id, { unit: e.target.value })}
              className="col-span-3 rounded-lg border border-input bg-white px-2 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {it.matched_product_id ? (
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {it.matched_sku} · €{(it.price || 0).toFixed(2)}/{it.unit} · riga €{((it.price || 0) * (it.quantity || 0)).toFixed(2)}
            </p>
          ) : suggestions.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="flex items-center gap-1 text-[11px] font-medium text-ai"><Sparkles size={11} /> Suggerimenti:</span>
              {suggestions.map((p) => (
                <button
                  key={p.id}
                  data-testid={`suggestion-${it.id}-${p.id}`}
                  onClick={() => onMatch(it.id, p.id)}
                  className="rounded-full border border-ai/30 bg-ai-soft px-2 py-0.5 text-[11px] font-medium text-ai hover:bg-ai hover:text-white transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OrderReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [products, setProducts] = useState([]);
  const [team, setTeam] = useState([]);
  const [saving, setSaving] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [emailDlg, setEmailDlg] = useState({ open: false, kind: "confirmation" });
  const [recipient, setRecipient] = useState("");
  const [emailMsg, setEmailMsg] = useState("");
  const [sending, setSending] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const load = useCallback(async () => {
    const [o, p, t] = await Promise.all([api.get(`/orders/${id}`), api.get("/products"), api.get("/team").catch(() => ({ data: [] }))]);
    setOrder(o.data);
    setProducts(p.data);
    setTeam(t.data);
  }, [id]);

  useEffect(() => { load().catch(() => toast.error("Impossibile caricare l'ordine")); }, [load]);

  const setItems = (fn) => setOrder((prev) => ({ ...prev, line_items: fn(prev.line_items) }));
  const onUpdate = (itemId, patch) => setItems((items) => items.map((it) => (it.id === itemId ? { ...it, ...patch } : it)));

  const onMatch = (itemId, productId) => {
    const p = products.find((x) => x.id === productId);
    if (!p) onUpdate(itemId, { matched_product_id: null, matched_sku: null, matched_name: null, price: 0, needs_review: true, confidence: 0 });
    else onUpdate(itemId, { matched_product_id: p.id, matched_sku: p.sku, matched_name: p.name, price: p.price, unit: p.unit || "unità", needs_review: false, confidence: 1 });
  };

  const onRemove = (itemId) => setItems((items) => items.filter((it) => it.id !== itemId));

  const onCreateProduct = async (itemId, name) => {
    const item = order.line_items.find((i) => i.id === itemId);
    const sku = `NEW-${crypto.randomUUID().slice(0, 6).toUpperCase()}`;
    try {
      const { data: p } = await api.post("/products", {
        sku, name, category: "General", unit: item?.unit || "unità", pack_size: "", price: 0, aliases: [],
      });
      setProducts((prev) => [...prev, p]);
      onUpdate(itemId, {
        matched_product_id: p.id, matched_sku: p.sku, matched_name: p.name,
        price: p.price, unit: p.unit || "unità", needs_review: false, confidence: 1,
      });
      toast.success(`Prodotto «${name}» creato e abbinato`);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };
  const onDuplicate = (itemId) => setItems((items) => {
    const idx = items.findIndex((it) => it.id === itemId);
    const copy = { ...items[idx], id: crypto.randomUUID() };
    return [...items.slice(0, idx + 1), copy, ...items.slice(idx + 1)];
  });
  const addItem = () => setItems((items) => [...items, {
    id: crypto.randomUUID(), raw_text: "", quantity: 1, unit: "unità",
    matched_product_id: null, matched_sku: null, matched_name: null, price: 0, confidence: 0, needs_review: true,
  }]);

  const onDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return;
    setItems((items) => {
      const oldIdx = items.findIndex((i) => i.id === active.id);
      const newIdx = items.findIndex((i) => i.id === over.id);
      return arrayMove(items, oldIdx, newIdx);
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(`/orders/${id}`, {
        customer_name: order.customer_name, delivery_date: order.delivery_date,
        notes: order.notes, line_items: order.line_items, assigned_to: order.assigned_to,
      });
      setOrder(data);
      toast.success("Modifiche salvate");
      return true;
    } catch (err) {
      toast.error(formatApiError(err));
      return false;
    } finally { setSaving(false); }
  };

  const openEmail = (kind) => {
    setExportOpen(false);
    setEmailDlg({ open: true, kind });
    setEmailMsg("");
  };

  const sendEmail = async () => {
    if (!recipient.trim()) return toast.error("Inserisci un'email destinatario.");
    setSending(true);
    try {
      await api.post(`/orders/${id}/send-email`, { recipient_email: recipient.trim(), message: emailMsg, kind: emailDlg.kind });
      toast.success(emailDlg.kind === "clarification" ? "Richiesta di chiarimento inviata" : "Email di conferma inviata");
      setEmailDlg({ open: false, kind: "confirmation" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setSending(false); }
  };

  const validate = async () => {
    if (!(await save())) return;
    try {
      const { data } = await api.post(`/orders/${id}/validate`);
      setOrder(data);
      toast.success("Ordine confermato");
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const doExport = async (format) => {
    setExportOpen(false);
    await save();
    const res = await fetch(`${API}/orders/${id}/export?format=${format}`, { credentials: "include" });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const ext = format === "excel" ? "xlsx" : format;
    a.href = url; a.download = `ordine-${id.slice(0, 8)}.${ext}`; a.click();
    URL.revokeObjectURL(url);
    toast.success(`Esportato in ${ext.toUpperCase()}`);
    load();
  };

  if (!order) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <div className="grid gap-6 lg:grid-cols-5">
          <Skeleton className="h-96 rounded-xl lg:col-span-2" />
          <Skeleton className="h-96 rounded-xl lg:col-span-3" />
        </div>
      </div>
    );
  }

  const total = order.line_items.reduce((s, i) => s + (i.price || 0) * (i.quantity || 0), 0);
  const reviewCount = order.line_items.filter((i) => i.needs_review).length;
  const isImage = (order.source_type === "file" || order.source_type === "image") && /\[Immagine/i.test(order.source_preview || "");

  return (
    <div className="animate-fade-up pb-24">
      <button data-testid="back-to-orders" onClick={() => navigate("/app/orders")} className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft size={16} /> Ordini
      </button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <input
              data-testid="customer-name-input"
              value={order.customer_name || ""}
              placeholder="Cliente sconosciuto"
              onChange={(e) => setOrder((p) => ({ ...p, customer_name: e.target.value }))}
              className="font-display text-2xl sm:text-3xl font-bold tracking-tight bg-transparent outline-none focus:bg-secondary/50 rounded px-1 -ml-1 max-w-full"
            />
            <StatusBadge status={order.status} />
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 font-mono text-xs text-muted-foreground">
            <span>ID {order.id.slice(0, 8)}</span>
            <span>·</span>
            <span>{order.line_items.length} articoli</span>
            <span>·</span>
            <span>consegna:</span>
            <input
              data-testid="delivery-date-input"
              value={order.delivery_date || ""}
              placeholder="—"
              onChange={(e) => setOrder((p) => ({ ...p, delivery_date: e.target.value }))}
              className="bg-transparent outline-none focus:bg-secondary/50 rounded px-1 w-28"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            data-testid="assignee-select"
            value={order.assigned_to || ""}
            onChange={(e) => setOrder((p) => ({ ...p, assigned_to: e.target.value || null }))}
            className="rounded-lg border border-input bg-white px-3 py-1.5 text-sm text-muted-foreground outline-none focus:ring-2 focus:ring-ring"
            title="Assegnatario"
          >
            <option value="">Non assegnato</option>
            {team.map((m) => (<option key={m.id} value={m.id}>{m.name}</option>))}
          </select>
          <button data-testid="toggle-history" onClick={() => setShowHistory((s) => !s)} className="flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground">
            <History size={15} /> Cronologia <ChevronDown size={14} className={cn("transition-transform", showHistory && "rotate-180")} />
          </button>
        </div>
      </div>

      {showHistory && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mb-4 overflow-hidden rounded-xl border border-border bg-white">
          <div className="divide-y divide-border" data-testid="history-panel">
            {(order.history || []).slice().reverse().map((h, i) => (
              <div key={`${h.ts}-${i}`} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span className="font-medium">{h.action}{h.detail ? <span className="text-muted-foreground font-normal"> · {h.detail}</span> : null}</span>
                <span className="font-mono text-xs text-muted-foreground">{new Date(h.ts).toLocaleString("it-IT")}</span>
              </div>
            ))}
            {(!order.history || order.history.length === 0) && <p className="px-4 py-3 text-sm text-muted-foreground">Nessuna attività.</p>}
          </div>
        </motion.div>
      )}

      {reviewCount > 0 && (
        <div data-testid="review-banner" className="mb-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <AlertTriangle size={17} />
          {reviewCount} {reviewCount === 1 ? "articolo richiede" : "articoli richiedono"} la tua conferma prima della validazione.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Source */}
        <div className="lg:col-span-2">
          <div className="sticky top-6 rounded-xl border border-border bg-white">
            <div className="flex items-center gap-2 border-b border-border px-4 py-3">
              {isImage ? <ImageIcon size={16} className="text-slate-400" /> : <FileText size={16} className="text-slate-400" />}
              <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">Sorgente originale</span>
              <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">{order.source_type}</span>
            </div>
            <pre data-testid="order-source" className="max-h-[540px] overflow-y-auto whitespace-pre-wrap p-4 font-mono text-sm leading-relaxed text-slate-700">
              {order.source_preview || "—"}
            </pre>
          </div>
        </div>

        {/* Editable table */}
        <div className="space-y-3 lg:col-span-3">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <SortableContext items={order.line_items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {order.line_items.map((it) => (
                  <SortableRow key={it.id} it={it} products={products}
                    onMatch={onMatch} onUpdate={onUpdate} onDuplicate={onDuplicate} onRemove={onRemove} onCreate={onCreateProduct} />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          <button
            data-testid="add-line-item"
            onClick={addItem}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-white py-2.5 text-sm text-muted-foreground transition-colors hover:border-slate-300 hover:text-foreground"
          >
            <Plus size={16} /> Aggiungi articolo
          </button>

          <div className="flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3">
            <span className="text-sm font-medium">Totale ordine</span>
            <span data-testid="order-total" className="font-display text-xl font-bold tracking-tight">€{total.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Action bar */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-border bg-white/85 backdrop-blur-xl md:left-[240px]">
        <div className="mx-auto flex max-w-[1600px] items-center justify-end gap-2 px-6 py-3 md:px-8">
          <button data-testid="save-order-button" onClick={save} disabled={saving} className="rounded-lg border border-input bg-white px-4 py-2 text-sm font-medium transition-colors hover:bg-secondary disabled:opacity-60">
            {saving ? "Salvataggio…" : "Salva"}
          </button>
          <div className="relative">
            <button data-testid="export-menu-button" onClick={() => setExportOpen((o) => !o)} className="flex items-center gap-1.5 rounded-lg border border-input bg-white px-4 py-2 text-sm font-medium transition-colors hover:bg-secondary">
              <Download size={16} /> Esporta <ChevronDown size={14} />
            </button>
            {exportOpen && (
              <div data-testid="export-menu" className="absolute bottom-full right-0 mb-2 w-52 overflow-hidden rounded-xl border border-border bg-white shadow-lg">
                {[["pdf", "PDF"], ["excel", "Excel"], ["csv", "CSV"], ["json", "JSON"]].map(([f, label]) => (
                  <button key={f} data-testid={`export-${f}-button`} onClick={() => doExport(f)} className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-secondary">
                    <Download size={14} className="text-muted-foreground" /> {label}
                  </button>
                ))}
                <div className="border-t border-border" />
                <button data-testid="export-email-button" onClick={() => openEmail("confirmation")} className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-secondary">
                  <Mail size={14} className="text-muted-foreground" /> Email conferma (PDF)
                </button>
                <button data-testid="request-clarification-button" onClick={() => openEmail("clarification")} className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-secondary">
                  <MessageSquare size={14} className="text-ai" /> Richiedi chiarimenti
                </button>
              </div>
            )}
          </div>
          <button data-testid="validate-order-button" onClick={validate} className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90">
            <CheckCircle2 size={16} /> Conferma ordine
          </button>
        </div>
      </div>

      <Dialog open={emailDlg.open} onOpenChange={(o) => setEmailDlg((d) => ({ ...d, open: o }))}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display tracking-tight flex items-center gap-2">
              {emailDlg.kind === "clarification" ? <><MessageSquare size={18} className="text-ai" /> Richiedi chiarimenti</> : <><Mail size={18} /> Invia conferma ordine</>}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Email destinatario</label>
              <input
                data-testid="email-recipient-input"
                type="email"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="cliente@esempio.it"
                className="mt-1.5 w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Messaggio (opzionale)</label>
              <textarea
                data-testid="email-message-input"
                rows={3}
                value={emailMsg}
                onChange={(e) => setEmailMsg(e.target.value)}
                placeholder={emailDlg.kind === "clarification" ? "Può confermare le quantità evidenziate?" : "Grazie per l'ordine!"}
                className="mt-1.5 w-full resize-none rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            {emailDlg.kind === "confirmation" && (
              <p className="text-xs text-muted-foreground">Verrà allegato il PDF dell'ordine.</p>
            )}
          </div>
          <DialogFooter>
            <button onClick={() => setEmailDlg((d) => ({ ...d, open: false }))} className="rounded-lg border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary">Annulla</button>
            <button data-testid="send-email-button" onClick={sendEmail} disabled={sending} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
              {sending ? "Invio…" : "Invia email"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
