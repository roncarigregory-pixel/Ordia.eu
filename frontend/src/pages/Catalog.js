import { useEffect, useState, useRef, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Upload, Search, Package } from "lucide-react";

const EMPTY = { sku: "", name: "", category: "General", unit: "unità", pack_size: "", price: 0, aliases: [] };

export default function Catalog() {
  const { t } = useI18n();
  const [products, setProducts] = useState(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const fileInput = useRef(null);

  const load = useCallback(() => api.get("/products").then(({ data }) => setProducts(data)).catch(() => setProducts([])), []);
  useEffect(() => { load(); }, [load]);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (p) => {
    setEditing(p);
    setForm({ ...p, aliases: p.aliases || [] });
    setOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) return toast.error(t("Il nome è obbligatorio."));
    const payload = {
      ...form,
      price: parseFloat(form.price) || 0,
      aliases: Array.isArray(form.aliases) ? form.aliases : String(form.aliases).split(",").map((a) => a.trim()).filter(Boolean),
    };
    try {
      if (editing) await api.put(`/products/${editing.id}`, payload);
      else await api.post("/products", payload);
      toast.success(editing ? t("Prodotto aggiornato") : t("Prodotto aggiunto"));
      setOpen(false);
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (p) => {
    await api.delete(`/products/${p.id}`);
    toast.success(t("Prodotto eliminato"));
    load();
  };

  const onImport = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try {
      const { data } = await api.post("/products/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(t("catalog.imported", { n: data.inserted }));
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      e.target.value = "";
    }
  };

  const filtered = (products || []).filter(
    (p) => !q || p.name.toLowerCase().includes(q.toLowerCase()) || (p.sku || "").toLowerCase().includes(q.toLowerCase())
  );

  const setF = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">{t("Catalogo")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("Prodotti, alias e formati che l'AI usa per abbinare gli ordini. Modificabile e sostituibile.")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input ref={fileInput} type="file" accept=".csv,.xlsx,.xls" className="hidden" data-testid="catalog-import-input" onChange={onImport} />
          <button data-testid="catalog-import-button" onClick={() => fileInput.current?.click()} className="flex items-center gap-2 rounded-lg border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary transition-colors">
            <Upload size={16} /> {t("Importa CSV/Excel")}
          </button>
          <button data-testid="catalog-add-button" onClick={openNew} className="flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2.5 text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus size={18} /> {t("Aggiungi prodotto")}
          </button>
        </div>
      </div>

      <div className="relative max-w-xs mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input data-testid="catalog-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Cerca per nome o SKU…")} className="w-full rounded-lg border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
      </div>

      <div className="rounded-xl border border-border bg-white overflow-hidden">
        {!products ? (
          <div className="p-4 space-y-3">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 rounded-md" />)}</div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center">
            <Package size={36} className="mx-auto text-slate-300" />
            <p className="mt-3 text-sm text-muted-foreground">{t("Nessun prodotto. Aggiungine uno o importa il tuo catalogo.")}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">SKU</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Prodotto")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden md:table-cell">{t("Formato")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden lg:table-cell">Alias</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground text-right">{t("Prezzo")}</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((p) => (
                <tr key={p.id} data-testid={`product-row-${p.id}`} className="hover:bg-secondary/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-muted-foreground">{p.sku}</td>
                  <td className="px-5 py-3 font-medium">
                    {p.name}
                    <span className="ml-2 text-xs text-muted-foreground">{p.category}</span>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground hidden md:table-cell">{p.pack_size}</td>
                  <td className="px-5 py-3 text-muted-foreground hidden lg:table-cell max-w-[200px] truncate">{(p.aliases || []).join(", ")}</td>
                  <td className="px-5 py-3 text-right font-mono">€{(p.price || 0).toFixed(2)}</td>
                  <td className="px-5 py-3 text-right">
                    <div className="inline-flex gap-1">
                      <button data-testid={`edit-product-${p.id}`} onClick={() => openEdit(p)} className="text-slate-400 hover:text-foreground p-1"><Pencil size={16} /></button>
                      <button data-testid={`delete-product-${p.id}`} onClick={() => remove(p)} className="text-slate-400 hover:text-red-500 p-1"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display tracking-tight">{editing ? t("Modifica prodotto") : t("Nuovo prodotto")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="SKU" testid="product-sku"><input value={form.sku} onChange={setF("sku")} className="input" /></Field>
              <Field label={t("Categoria")} testid="product-category"><input value={form.category} onChange={setF("category")} className="input" /></Field>
            </div>
            <Field label={t("Nome")} testid="product-name"><input value={form.name} onChange={setF("name")} className="input" /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Unità")} testid="product-unit"><input value={form.unit} onChange={setF("unit")} className="input" /></Field>
              <Field label={t("Prezzo (€)")} testid="product-price"><input type="number" step="0.01" value={form.price} onChange={setF("price")} className="input" /></Field>
            </div>
            <Field label={t("Formato confezione")} testid="product-pack"><input value={form.pack_size} onChange={setF("pack_size")} placeholder="es. 1 cassa = 12 kg" className="input" /></Field>
            <Field label={t("Alias (separati da virgola)")} testid="product-aliases">
              <input
                value={Array.isArray(form.aliases) ? form.aliases.join(", ") : form.aliases}
                onChange={(e) => setForm({ ...form, aliases: e.target.value.split(",").map((a) => a.trim()) })}
                placeholder="mozz, mozzarella, formaggio pizza"
                className="input"
              />
            </Field>
          </div>
          <DialogFooter>
            <button onClick={() => setOpen(false)} className="rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary">{t("Annulla")}</button>
            <button data-testid="save-product-button" onClick={save} className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90">{t("Salva")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <style>{`.input{width:100%;border-radius:0.375rem;border:1px solid hsl(var(--input));background:white;padding:0.5rem 0.75rem;font-size:0.875rem;outline:none}.input:focus{box-shadow:0 0 0 2px hsl(var(--ring))}`}</style>
    </div>
  );
}

function Field({ label, testid, children }) {
  return (
    <div data-testid={testid}>
      <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{label}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}
