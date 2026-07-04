import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Users, ArrowUpRight, Upload, Loader2, RefreshCw, Download } from "lucide-react";

export default function Customers() {
  const [customers, setCustomers] = useState(null);
  const [q, setQ] = useState("");
  const [importing, setImporting] = useState(false);
  const fileRef = useRef(null);
  const navigate = useNavigate();

  const loadCustomers = () =>
    api.get("/customers").then(({ data }) => setCustomers(data)).catch(() => setCustomers([]));

  useEffect(() => { loadCustomers(); }, []);

  const downloadModel = () => {
    const csv = "cliente,prodotto,quantità\n" +
      "Trattoria Sole,Mozzarella Block,8\n" +
      "Trattoria Sole,Chopped Tomatoes Tin,5\n" +
      "Trattoria Sole,Extra Virgin Olive Oil,1\n" +
      "Pizzeria Roma,All-Purpose Flour,3\n" +
      "Pizzeria Roma,Mozzarella Block,10\n";
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "modello-clienti-ordia.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/customers/import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`${data.customers} clienti importati · ${data.products_linked} prodotti abbinati` +
        (data.unmatched_count ? ` · ${data.unmatched_count} righe non abbinate` : ""));
      await loadCustomers();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Import non riuscito. Controlla il formato del file.");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const filtered = useMemo(
    () => (customers || []).filter((c) => !q || c.name.toLowerCase().includes(q.toLowerCase())),
    [customers, q]
  );

  return (
    <div className="animate-fade-up">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">Clienti</h1>
          <p className="mt-1 text-sm text-muted-foreground">Storico ordini, volumi e prodotti abituali per ogni cliente.</p>
        </div>
        <div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleImport}
            className="hidden"
            data-testid="import-customers-input"
          />
          <button
            data-testid="import-customers-button"
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            className="flex items-center gap-2 rounded-lg border border-input bg-white px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-secondary disabled:opacity-60"
          >
            {importing ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {importing ? "Importazione…" : "Importa clienti"}
          </button>
          <button
            data-testid="download-template-button"
            onClick={downloadModel}
            className="mt-2 flex w-full items-center justify-center gap-1.5 text-xs font-medium text-primary hover:underline"
          >
            <Download size={13} /> Scarica il modello CSV
          </button>
          <p className="mt-1 text-right text-xs text-muted-foreground">CSV/Excel · colonne: cliente, prodotto, quantità</p>
        </div>
      </div>

      {customers && customers.filter((c) => c.needs_reorder).length > 0 && (
        <div data-testid="reorder-alert" className="mb-4 flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <RefreshCw size={16} className="shrink-0" />
          <span>
            <span className="font-semibold">{customers.filter((c) => c.needs_reorder).length} clienti</span> non ordinano da un po'. Aprili e proponi un <span className="font-semibold">riordino con un click</span>.
          </span>
        </div>
      )}

      <div className="relative max-w-xs mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          data-testid="customers-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Cerca cliente…"
          className="w-full rounded-lg border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {!customers ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-border bg-white p-16 text-center">
          <Users size={32} className="mx-auto text-slate-300" />
          <p className="mt-3 text-sm text-muted-foreground">Nessun cliente. I clienti compaiono automaticamente dagli ordini.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <button
              key={c.name}
              data-testid={`customer-card-${c.name}`}
              onClick={() => navigate(`/app/customers/${encodeURIComponent(c.name)}`)}
              className="group rounded-xl border border-border bg-white p-5 text-left transition-all hover:border-slate-300 hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {c.name.slice(0, 2).toUpperCase()}
                </div>
                {c.needs_reorder ? (
                  <span data-testid={`reorder-badge-${c.name}`} className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-700">
                    <RefreshCw size={11} />
                    {c.days_since_last_order != null ? `Da riordinare · ${c.days_since_last_order}gg` : "Da riordinare"}
                  </span>
                ) : (
                  <ArrowUpRight size={16} className="text-slate-300 transition-colors group-hover:text-primary" />
                )}
              </div>
              <p className="mt-3 truncate font-semibold">{c.name}</p>
              <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                <span><span className="font-mono font-medium text-foreground">{c.orders}</span> ordini</span>
                <span><span className="font-mono font-medium text-foreground">€{(c.volume || 0).toFixed(0)}</span> volume</span>
              </div>
              {c.favorite_products?.length > 0 && (
                <p className="mt-2 truncate text-xs text-muted-foreground">Abituali: {c.favorite_products.join(", ")}</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
