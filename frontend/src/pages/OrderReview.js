import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft, CheckCircle, Trash, Plus, DownloadSimple, WarningCircle, FileText,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

function confColor(c) {
  if (c >= 0.8) return "text-emerald-600";
  if (c >= 0.5) return "text-amber-600";
  return "text-red-600";
}

export default function OrderReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [products, setProducts] = useState([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [o, p] = await Promise.all([api.get(`/orders/${id}`), api.get("/products")]);
    setOrder(o.data);
    setProducts(p.data);
  }, [id]);

  useEffect(() => {
    load().catch(() => toast.error("Impossibile caricare l'ordine"));
  }, [load]);

  const updateItem = (itemId, patch) => {
    setOrder((prev) => ({
      ...prev,
      line_items: prev.line_items.map((it) => (it.id === itemId ? { ...it, ...patch } : it)),
    }));
  };

  const onMatchChange = (itemId, productId) => {
    const p = products.find((x) => x.id === productId);
    if (!p) {
      updateItem(itemId, { matched_product_id: null, matched_sku: null, matched_name: null, price: 0, needs_review: true, confidence: 0 });
    } else {
      updateItem(itemId, {
        matched_product_id: p.id, matched_sku: p.sku, matched_name: p.name,
        price: p.price, unit: p.unit, needs_review: false, confidence: 1,
      });
    }
  };

  const removeItem = (itemId) =>
    setOrder((prev) => ({ ...prev, line_items: prev.line_items.filter((it) => it.id !== itemId) }));

  const addItem = () =>
    setOrder((prev) => ({
      ...prev,
      line_items: [
        ...prev.line_items,
        { id: crypto.randomUUID(), raw_text: "", quantity: 1, unit: "unità", matched_product_id: null, matched_sku: null, matched_name: null, price: 0, confidence: 0, needs_review: true },
      ],
    }));

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(`/orders/${id}`, {
        customer_name: order.customer_name,
        delivery_date: order.delivery_date,
        notes: order.notes,
        line_items: order.line_items,
      });
      setOrder(data);
      toast.success("Modifiche salvate");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const validate = async () => {
    await save();
    try {
      const { data } = await api.post(`/orders/${id}/validate`);
      setOrder(data);
      toast.success("Ordine validato");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const doExport = async (format) => {
    await save();
    const token = localStorage.getItem("ordia_token");
    const res = await fetch(`${API}/orders/${id}/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ordine-${id.slice(0, 8)}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Esportato in ${format.toUpperCase()}`);
    load();
  };

  if (!order) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64 rounded-md" />
        <div className="grid lg:grid-cols-2 gap-6">
          <Skeleton className="h-96 rounded-md" />
          <Skeleton className="h-96 rounded-md" />
        </div>
      </div>
    );
  }

  const total = order.line_items.reduce((s, i) => s + (i.price || 0) * (i.quantity || 0), 0);
  const reviewCount = order.line_items.filter((i) => i.needs_review).length;

  return (
    <div className="animate-fade-up pb-24">
      <button data-testid="back-to-orders" onClick={() => navigate("/app/orders")} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft size={16} /> Ordini
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-3xl font-black tracking-tighter">
              {order.customer_name || "Cliente sconosciuto"}
            </h1>
            <StatusBadge status={order.status} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground font-mono">
            ID {order.id.slice(0, 8)} · {order.line_items.length} articoli
            {order.delivery_date ? ` · consegna: ${order.delivery_date}` : ""}
          </p>
        </div>
      </div>

      {reviewCount > 0 && (
        <div data-testid="review-banner" className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <WarningCircle size={18} weight="fill" />
          {reviewCount} {reviewCount === 1 ? "articolo richiede" : "articoli richiedono"} la tua conferma prima della validazione.
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Source */}
        <div className="lg:col-span-2">
          <div className="rounded-md border border-border bg-white sticky top-6">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <FileText size={18} className="text-slate-400" />
              <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Sorgente originale</span>
            </div>
            <pre data-testid="order-source" className="p-4 text-sm font-mono whitespace-pre-wrap leading-relaxed text-slate-700 max-h-[520px] overflow-y-auto">
              {order.source_preview || "—"}
            </pre>
          </div>
        </div>

        {/* Line items */}
        <div className="lg:col-span-3 space-y-3">
          {order.line_items.map((it) => (
            <div
              key={it.id}
              data-testid={`line-item-${it.id}`}
              className={cn(
                "rounded-md border bg-white p-4 transition-colors",
                it.needs_review ? "border-amber-200" : "border-border hover:border-slate-300"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs text-muted-foreground font-mono flex-1 truncate" title={it.raw_text}>
                  “{it.raw_text || "riga manuale"}”
                </p>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={cn("text-xs font-mono font-medium", confColor(it.confidence))}>
                    {Math.round((it.confidence || 0) * 100)}%
                  </span>
                  <button data-testid={`remove-item-${it.id}`} onClick={() => removeItem(it.id)} className="text-slate-300 hover:text-red-500 transition-colors">
                    <Trash size={16} />
                  </button>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-12 gap-2 items-center">
                <select
                  data-testid={`match-select-${it.id}`}
                  value={it.matched_product_id || ""}
                  onChange={(e) => onMatchChange(it.id, e.target.value)}
                  className={cn(
                    "col-span-7 rounded-md border bg-white px-2.5 py-2 text-sm outline-none focus:ring-2 focus:ring-ring",
                    it.matched_product_id ? "border-input" : "border-amber-300 text-amber-700"
                  )}
                >
                  <option value="">— Nessun abbinamento —</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.sku})
                    </option>
                  ))}
                </select>
                <input
                  data-testid={`qty-input-${it.id}`}
                  type="number"
                  min="0"
                  step="0.5"
                  value={it.quantity}
                  onChange={(e) => updateItem(it.id, { quantity: parseFloat(e.target.value) || 0 })}
                  className="col-span-2 rounded-md border border-input bg-white px-2 py-2 text-sm font-mono text-center outline-none focus:ring-2 focus:ring-ring"
                />
                <input
                  data-testid={`unit-input-${it.id}`}
                  value={it.unit}
                  onChange={(e) => updateItem(it.id, { unit: e.target.value })}
                  className="col-span-3 rounded-md border border-input bg-white px-2 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              {it.matched_product_id && (
                <p className="mt-2 text-xs text-muted-foreground font-mono">
                  {it.matched_sku} · €{(it.price || 0).toFixed(2)}/{it.unit} · riga €{((it.price || 0) * (it.quantity || 0)).toFixed(2)}
                </p>
              )}
            </div>
          ))}

          <button
            data-testid="add-line-item"
            onClick={addItem}
            className="w-full flex items-center justify-center gap-2 rounded-md border border-dashed border-border bg-white py-2.5 text-sm text-muted-foreground hover:border-slate-300 hover:text-foreground transition-colors"
          >
            <Plus size={16} /> Aggiungi articolo
          </button>

          <div className="flex items-center justify-between rounded-md border border-border bg-white px-4 py-3">
            <span className="text-sm font-medium">Totale ordine</span>
            <span data-testid="order-total" className="font-display text-xl font-black tracking-tight">€{total.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Action bar */}
      <div className="fixed bottom-0 left-0 md:left-[240px] right-0 border-t border-border bg-white/80 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto flex items-center justify-end gap-2 px-6 md:px-8 py-3">
          <button data-testid="save-order-button" onClick={save} disabled={saving} className="rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary disabled:opacity-60 transition-colors">
            {saving ? "Salvataggio…" : "Salva"}
          </button>
          <button data-testid="export-csv-button" onClick={() => doExport("csv")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary transition-colors">
            <DownloadSimple size={16} /> CSV
          </button>
          <button data-testid="export-json-button" onClick={() => doExport("json")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary transition-colors">
            <DownloadSimple size={16} /> JSON
          </button>
          <button data-testid="validate-order-button" onClick={validate} className="flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors">
            <CheckCircle size={16} weight="fill" /> Valida ordine
          </button>
        </div>
      </div>
    </div>
  );
}
