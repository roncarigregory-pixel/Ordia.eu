import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Search, Package, Sparkles, RefreshCw, Server, Loader2, History, CircleCheck, CircleDashed, CircleAlert } from "lucide-react";
import { CatalogImportWizard } from "@/components/CatalogImportWizard";

const EMPTY = { sku: "", name: "", category: "General", unit: "unità", pack_size: "", price: 0, aliases: [] };

const STATUS_META = {
  absent: { label: "Catalogo assente", cls: "bg-slate-100 text-slate-600", icon: CircleDashed },
  incomplete: { label: "Catalogo incompleto", cls: "bg-amber-50 text-amber-600", icon: CircleAlert },
  ready: { label: "Catalogo pronto", cls: "bg-emerald-50 text-emerald-600", icon: CircleCheck },
};

export default function Catalog() {
  const { t } = useI18n();
  const [products, setProducts] = useState(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [imports, setImports] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);
  const [togglingSync, setTogglingSync] = useState(false);

  const load = useCallback(() => api.get("/products").then(({ data }) => setProducts(data)).catch(() => setProducts([])), []);
  const loadSync = useCallback(() => api.get("/catalog/sync-status").then(({ data }) => setSyncStatus(data)).catch(() => setSyncStatus(null)), []);
  const loadStatus = useCallback(() => api.get("/catalog/status").then(({ data }) => setStatus(data)).catch(() => setStatus(null)), []);
  const loadImports = useCallback(() => api.get("/catalog/imports").then(({ data }) => setImports(data.items || [])).catch(() => setImports([])), []);
  useEffect(() => { load(); loadSync(); loadStatus(); loadImports(); }, [load, loadSync, loadStatus, loadImports]);

  const onImportDone = () => { load(); loadStatus(); loadImports(); };

  const [searchParams, setSearchParams] = useSearchParams();
  useEffect(() => {
    if (searchParams.get("import") === "1") {
      setWizardOpen(true);
      searchParams.delete("import");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const toggleAutosync = async () => {
    if (!syncStatus) return;
    setTogglingSync(true);
    try {
      const next = !syncStatus.autosync;
      await api.put("/catalog/autosync", { enabled: next });
      setSyncStatus((s) => ({ ...s, autosync: next }));
      toast.success(next ? t("Sincronizzazione automatica attivata.") : t("Sincronizzazione automatica disattivata."));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setTogglingSync(false);
    }
  };

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
      onImportDone();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (p) => {
    await api.delete(`/products/${p.id}`);
    toast.success(t("Prodotto eliminato"));
    onImportDone();
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
          <button data-testid="catalog-import-button" onClick={() => setWizardOpen(true)} className="flex items-center gap-2 rounded-lg border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary transition-colors">
            <Sparkles size={16} className="text-ai" /> {t("Importa catalogo")}
          </button>
          <button data-testid="catalog-add-button" onClick={openNew} className="flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2.5 text-sm font-semibold hover:bg-primary/90 transition-colors">
            <Plus size={18} /> {t("Aggiungi prodotto")}
          </button>
        </div>
      </div>

      {status && (
        <div data-testid="catalog-status" className="mb-4 flex flex-wrap items-center gap-2">
          {(() => { const m = STATUS_META[status.status] || STATUS_META.absent; const Icon = m.icon; return (
            <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${m.cls}`}>
              <Icon size={14} /> {t(m.label)}
            </span>
          ); })()}
          {status.total > 0 && <span className="text-xs text-muted-foreground">{status.total} {t("prodotti")}{status.missing_price > 0 ? ` · ${status.missing_price} ${t("senza prezzo")}` : ""}</span>}
          {status.status === "absent" && <span className="text-xs text-muted-foreground">{t("Importa il catalogo per iniziare a ricevere ordini precisi.")}</span>}
        </div>
      )}

      {syncStatus && (
        <div data-testid="catalog-erp-sync" className="mb-4 rounded-xl border border-border bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ai/10 text-ai">
                <Server size={18} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold">{t("Sincronizzazione catalogo dal gestionale")}</h2>
                  <span
                    data-testid="catalog-sync-bridge-status"
                    className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${syncStatus.bridge_connected ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${syncStatus.bridge_connected ? "bg-emerald-500" : "bg-slate-400"}`} />
                    {syncStatus.bridge_connected ? t("Bridge collegato") : t("Bridge non collegato")}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {syncStatus.bridge_connected
                    ? t("catalog.syncConnected", { erp: syncStatus.erp_name || "ERP" })
                    : t("Collega il Bridge per importare e mantenere aggiornato il catalogo automaticamente dal tuo gestionale.")}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span data-testid="catalog-sync-count">{t("catalog.syncCount", { n: syncStatus.product_count })}</span>
                  {syncStatus.last_sync ? (
                    <span data-testid="catalog-sync-last">
                      {t("Ultima sincronizzazione")}: {new Date(syncStatus.last_sync).toLocaleString("it-IT")}
                      {syncStatus.last_sync_stats ? ` (+${syncStatus.last_sync_stats.inserted}, ↻${syncStatus.last_sync_stats.updated})` : ""}
                    </span>
                  ) : (
                    <span data-testid="catalog-sync-last">{t("Nessuna sincronizzazione ancora")}</span>
                  )}
                </div>
              </div>
            </div>
            <button
              data-testid="catalog-autosync-toggle"
              onClick={toggleAutosync}
              disabled={togglingSync}
              className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:opacity-60 ${syncStatus.autosync ? "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "border-input bg-white text-foreground hover:bg-secondary"}`}
            >
              {togglingSync ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
              {syncStatus.autosync ? t("Auto-sync attivo") : t("Auto-sync disattivo")}
            </button>
          </div>
        </div>
      )}

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
            <p className="mt-3 text-sm font-medium text-foreground">{t("Non serve configurare nulla per iniziare.")}</p>
            <p className="mt-1 text-sm text-muted-foreground max-w-md mx-auto">{t("Inizia a caricare gli ordini: Ordia imparerà il tuo catalogo da solo. Oppure importalo subito da una foto, un PDF o un Excel.")}</p>
            <div className="mt-5 flex items-center justify-center gap-2">
              <button data-testid="catalog-empty-import" onClick={() => setWizardOpen(true)} className="inline-flex items-center gap-2 rounded-lg bg-ai text-white px-4 py-2.5 text-sm font-semibold hover:bg-ai/90 transition-colors">
                <Sparkles size={16} /> {t("Importa catalogo")}
              </button>
              <button data-testid="catalog-empty-add" onClick={openNew} className="inline-flex items-center gap-2 rounded-lg border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary transition-colors">
                <Plus size={16} /> {t("Aggiungi manualmente")}
              </button>
            </div>
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

      {imports.length > 0 && (
        <div data-testid="catalog-import-history" className="mt-6">
          <div className="flex items-center gap-2 mb-2">
            <History size={16} className="text-slate-400" />
            <h2 className="font-display text-lg font-bold tracking-tight">{t("Storico importazioni")}</h2>
          </div>
          <div className="rounded-xl border border-border bg-white divide-y divide-border">
            {imports.slice(0, 8).map((im) => (
              <div key={im.id} data-testid={`import-log-${im.id}`} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm">
                <span className="text-muted-foreground">{new Date(im.created_at).toLocaleString("it-IT")}</span>
                <span className="text-xs text-foreground">
                  {im.mode === "update" ? t("Aggiornamento") : t("Aggiunta")} · +{im.inserted} {t("nuovi")}
                  {im.updated ? `, ↻${im.updated} ${t("aggiornati")}` : ""}
                  {im.skipped ? `, ${im.skipped} ${t("saltati")}` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <CatalogImportWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onDone={onImportDone} />

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
