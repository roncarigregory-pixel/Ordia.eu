import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Search, ChevronRight, ChevronLeft, Check, CheckCircle2, AlertTriangle, AlertOctagon, ArrowDownWideNarrow } from "lucide-react";

// Mini stepper compatto per riga: Ricevuto → Confermato → Inviato → Consegnato
function MiniTimeline({ status, delivered, t }) {
  const confirmed = status === "validated" || status === "exported";
  const sent = status === "exported";
  const steps = [
    { key: "received", done: status !== "processing", current: status === "processing" },
    { key: "confirmed", done: confirmed, current: status === "needs_review" || status === "ready" },
    { key: "sent", done: sent, current: status === "validated" },
    { key: "delivered", done: !!delivered, current: sent && !delivered },
  ];
  return (
    <div data-testid="order-mini-timeline" className="flex items-center" title={t("Ricevuto → Confermato → Inviato → Consegnato")}>
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <span className={
            "flex h-4 w-4 items-center justify-center rounded-full transition-colors " +
            (s.done ? "bg-emerald-500 text-white"
              : s.current ? "bg-ai text-white ring-2 ring-ai/20"
              : "bg-slate-200 text-transparent")
          }>
            {s.done ? <Check size={10} strokeWidth={3} /> : <span className="h-1.5 w-1.5 rounded-full bg-white/70" />}
          </span>
          {i < steps.length - 1 && (
            <div className={"mx-0.5 h-0.5 w-4 lg:w-6 rounded " + (s.done ? "bg-emerald-400" : "bg-slate-200")} />
          )}
        </div>
      ))}
    </div>
  );
}

// Pallina di affidabilità per riga (usa il bucket calcolato dal backend, coerente con le card)
function ReliabilityDot({ order, t }) {
  const bucket = order.bucket;
  const pct = order.reliability ?? 0;
  const review = order.review_count ?? 0;
  const map = {
    green: { color: "bg-emerald-500", label: t("Pronto da inviare") },
    amber: { color: "bg-amber-500", label: `${t("Affidabilità")} ${pct}% · ${review} ${t("da confermare")}` },
    red: { color: "bg-red-500", label: `${t("Critico")} · ${t("Affidabilità")} ${pct}%` },
    done: { color: "bg-emerald-500/60", label: t("Inviato al gestionale") },
    pending: { color: "bg-slate-300", label: t("In lavorazione…") },
  };
  const m = map[bucket] || map.pending;
  return (
    <span data-testid={`order-reliability-${order.id}`} className="inline-flex items-center gap-1.5" title={m.label}>
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${m.color}`} />
      {(bucket === "amber" || bucket === "red") && <span className="hidden text-xs font-medium tabular-nums text-muted-foreground xl:inline">{pct}%</span>}
    </span>
  );
}


const TONES = {
  emerald: { ring: "ring-emerald-400", activeBg: "bg-emerald-50 border-emerald-300", icon: "text-emerald-600", count: "text-emerald-700" },
  amber: { ring: "ring-amber-400", activeBg: "bg-amber-50 border-amber-300", icon: "text-amber-600", count: "text-amber-700" },
  red: { ring: "ring-red-400", activeBg: "bg-red-50 border-red-300", icon: "text-red-600", count: "text-red-700" },
};

function OpsCard({ icon: Icon, count, title, hint, tone, active, onClick, testid }) {
  const c = TONES[tone];
  return (
    <button data-testid={testid} onClick={onClick}
      className={`group flex items-center gap-4 rounded-xl border p-4 text-left transition-all ${active ? `${c.activeBg} ring-2 ${c.ring}` : "border-border bg-white hover:border-slate-300 hover:shadow-sm"}`}>
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-secondary ${c.icon}`}>
        <Icon size={22} />
      </div>
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className={`font-display text-2xl font-black tabular-nums ${c.count}`}>{count}</span>
          <span className="text-sm font-semibold text-foreground">{title}</span>
        </div>
        <p className="truncate text-xs text-muted-foreground">{hint}</p>
      </div>
    </button>
  );
}

const FILTERS = [
  { key: "all", label: "Tutti" },
  { key: "needs_review", label: "Da Revisionare" },
  { key: "ready", label: "Pronti" },
  { key: "validated", label: "Validati" },
  { key: "exported", label: "Esportati" },
];

const DELIVERY_FILTERS = [
  { key: "all", label: "Consegna: Tutte" },
  { key: "not_delivered", label: "Non consegnati" },
  { key: "in_progress", label: "In consegna" },
  { key: "delivered", label: "Consegnati" },
  { key: "failed", label: "Falliti" },
];

const PAGE_SIZE = 25;

export default function Orders() {
  const [data, setData] = useState(null); // { items, total, limit, skip }
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [delivery, setDelivery] = useState("all");
  const [bucket, setBucket] = useState("all");
  const [criticalFirst, setCriticalFirst] = useState(false);
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
  useEffect(() => { setPage(0); }, [filter, delivery, bucket, criticalFirst, debouncedQ]);

  useEffect(() => {
    setLoading(true);
    api
      .get("/orders", { params: { limit: PAGE_SIZE, skip: page * PAGE_SIZE, status: filter, delivery, bucket, sort: criticalFirst ? "critical" : "recent", q: debouncedQ } })
      .then(({ data }) => setData(data))
      .catch(() => setData({ items: [], total: 0, limit: PAGE_SIZE, skip: 0, summary: { green: 0, amber: 0, red: 0 } }))
      .finally(() => setLoading(false));
  }, [filter, delivery, bucket, criticalFirst, debouncedQ, page]);

  const items = data?.items || [];
  const total = data?.total || 0;
  const summary = data?.summary || { green: 0, amber: 0, red: 0 };
  const onCard = (b) => { setBucket((cur) => (cur === b ? "all" : b)); setFilter("all"); };
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

      {/* Dashboard operativa: 3 card cliccabili per capire in 5 secondi dove intervenire */}
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <OpsCard testid="ops-card-green" active={bucket === "green"} onClick={() => onCard("green")}
          icon={CheckCircle2} count={summary.green} title={t("Pronti da inviare")}
          tone="emerald" hint={t("Affidabili, li puoi inviare al gestionale")} />
        <OpsCard testid="ops-card-amber" active={bucket === "amber"} onClick={() => onCard("amber")}
          icon={AlertTriangle} count={summary.amber} title={t("Da confermare")}
          tone="amber" hint={t("Serve un rapido controllo prima dell'invio")} />
        <OpsCard testid="ops-card-red" active={bucket === "red"} onClick={() => onCard("red")}
          icon={AlertOctagon} count={summary.red} title={t("Critici")}
          tone="red" hint={t("Bassa affidabilità: da sistemare")} />
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
        <button
          data-testid="orders-sort-critical"
          onClick={() => setCriticalFirst((v) => !v)}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${criticalFirst ? "border-ai bg-ai/5 text-ai" : "border-input bg-white text-foreground hover:bg-secondary"}`}
        >
          <ArrowDownWideNarrow size={15} /> {t("Mostra prima quelli da controllare")}
        </button>
        <div className="relative flex-1 max-w-xs sm:ml-auto">
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

      <div className="mb-4 inline-flex flex-wrap gap-1 rounded-md border border-border bg-white p-1">
        {DELIVERY_FILTERS.map((f) => (
          <button
            key={f.key}
            data-testid={`delivery-filter-${f.key}`}
            onClick={() => setDelivery(f.key)}
            className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${delivery === f.key ? "bg-emerald-50 text-emerald-700" : "text-muted-foreground hover:text-foreground"}`}
          >
            {t(f.label)}
          </button>
        ))}
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
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden lg:table-cell">{t("Avanzamento")}</th>
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
                  <td className="px-5 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      <ReliabilityDot order={o} t={t} />
                      {o.customer_name || t("Cliente sconosciuto")}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground font-mono hidden sm:table-cell">{o.line_items.length}</td>
                  <td className="px-5 py-3 text-muted-foreground hidden md:table-cell">{t(`ch.${o.source_type}`)}</td>
                  <td className="px-5 py-3"><StatusBadge status={o.status} /></td>
                  <td className="px-5 py-3 hidden lg:table-cell"><MiniTimeline status={o.status} delivered={o.delivery_status === "delivered"} t={t} /></td>
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
