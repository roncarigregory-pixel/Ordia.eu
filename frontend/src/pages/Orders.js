import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Search, ChevronRight, ChevronLeft } from "lucide-react";

const FILTERS = [
  { key: "all", label: "Tutti" },
  { key: "needs_review", label: "Da Revisionare" },
  { key: "ready", label: "Pronti" },
  { key: "validated", label: "Validati" },
  { key: "exported", label: "Esportati" },
];

const PAGE_SIZE = 25;

export default function Orders() {
  const [data, setData] = useState(null); // { items, total, limit, skip }
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(0);
  const navigate = useNavigate();
  const { t } = useI18n();

  // Debounce the search input to avoid a request on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 350);
    return () => clearTimeout(t);
  }, [q]);

  // Reset to first page whenever filter/search changes.
  useEffect(() => { setPage(0); }, [filter, debouncedQ]);

  useEffect(() => {
    setLoading(true);
    api
      .get("/orders", { params: { limit: PAGE_SIZE, skip: page * PAGE_SIZE, status: filter, q: debouncedQ } })
      .then(({ data }) => setData(data))
      .catch(() => setData({ items: [], total: 0, limit: PAGE_SIZE, skip: 0 }))
      .finally(() => setLoading(false));
  }, [filter, debouncedQ, page]);

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min(total, page * PAGE_SIZE + items.length);

  return (
    <div className="animate-fade-up">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">{t("Ordini")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("Tutti gli ordini in arrivo, estratti e pronti da verificare.")}</p>
        </div>
        <button
          data-testid="orders-new-order"
          onClick={() => navigate("/app/new")}
          className="flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2.5 text-sm font-semibold hover:bg-primary/90 transition-colors"
        >
          <Plus size={18} /> {t("Nuovo Ordine")}
        </button>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <div className="inline-flex flex-wrap gap-1 rounded-md border border-border bg-white p-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              data-testid={`filter-${f.key}`}
              onClick={() => setFilter(f.key)}
              className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${filter === f.key ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              {t(f.label)}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            data-testid="orders-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("Cerca cliente…")}
            className="w-full rounded-lg border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div className="rounded-xl border border-border bg-white overflow-hidden">
        {loading && !data ? (
          <div className="p-4 space-y-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12 rounded-md" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="p-16 text-center text-sm text-muted-foreground">{t("Nessun ordine trovato.")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Cliente")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden sm:table-cell">{t("Articoli")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden md:table-cell">{t("Sorgente")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Stato")}</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((o) => (
                <tr
                  key={o.id}
                  data-testid={`order-row-${o.id}`}
                  onClick={() => navigate(`/app/orders/${o.id}`)}
                  className="cursor-pointer hover:bg-secondary/50 transition-colors"
                >
                  <td className="px-5 py-3 font-medium">{o.customer_name || t("Cliente sconosciuto")}</td>
                  <td className="px-5 py-3 text-muted-foreground font-mono hidden sm:table-cell">{o.line_items.length}</td>
                  <td className="px-5 py-3 text-muted-foreground hidden md:table-cell capitalize">{o.source_type}</td>
                  <td className="px-5 py-3"><StatusBadge status={o.status} /></td>
                  <td className="px-5 py-3 text-right"><ChevronRight size={16} className="text-slate-300 inline" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {total > 0 && (
        <div data-testid="orders-pagination" className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span data-testid="orders-range">{t("orders.range", { from, to, total })}</span>
          <div className="flex items-center gap-2">
            <button
              data-testid="orders-prev-page"
              disabled={page === 0 || loading}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="flex items-center gap-1 rounded-lg border border-border bg-white px-3 py-1.5 font-medium text-foreground transition-colors hover:bg-secondary/50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft size={15} /> {t("Precedente")}
            </button>
            <span data-testid="orders-page-indicator" className="tabular-nums">{t("orders.pageIndicator", { page: page + 1, pages: totalPages })}</span>
            <button
              data-testid="orders-next-page"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-lg border border-border bg-white px-3 py-1.5 font-medium text-foreground transition-colors hover:bg-secondary/50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {t("Successiva")} <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
