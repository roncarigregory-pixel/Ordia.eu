import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tray, ClockCountdown, CheckCircle, Target, Plus, ArrowUpRight } from "@phosphor-icons/react";

function Kpi({ label, value, sub, icon: Icon, testid }) {
  return (
    <div data-testid={testid} className="rounded-md border border-border bg-white p-5 transition-colors hover:border-slate-300">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{label}</span>
        <Icon size={18} className="text-slate-400" />
      </div>
      <p className="mt-3 font-display text-3xl font-black tracking-tighter">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/dashboard/stats").then(({ data }) => setStats(data)).catch(() => {});
  }, []);

  return (
    <div className="animate-fade-up">
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="font-display text-4xl font-black tracking-tighter">Centro di Comando</h1>
          <p className="mt-1 text-sm text-muted-foreground">Ogni ordine estratto e pronto per una verifica con un clic.</p>
        </div>
        <button
          data-testid="dashboard-new-order"
          onClick={() => navigate("/app/new")}
          className="hidden sm:flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus size={18} weight="bold" /> Nuovo Ordine
        </button>
      </div>

      {!stats ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-md" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Kpi testid="kpi-hours-saved" label="Ore Risparmiate" value={`${stats.hours_saved}h`} sub="rispetto all'inserimento manuale" icon={ClockCountdown} />
          <Kpi testid="kpi-total-orders" label="Ordini" value={stats.total_orders} sub={`${stats.processed} elaborati`} icon={Tray} />
          <Kpi testid="kpi-needs-review" label="Da Revisionare" value={stats.needs_review} sub="in attesa di conferma" icon={CheckCircle} />
          <Kpi testid="kpi-accuracy" label="Precisione Match" value={`${stats.accuracy}%`} sub="confidenza media AI" icon={Target} />
        </div>
      )}

      <div className="rounded-md border border-border bg-white">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-display text-lg font-bold tracking-tight">Ordini Recenti</h2>
          <button data-testid="view-all-orders" onClick={() => navigate("/app/orders")} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
            Vedi tutti <ArrowUpRight size={14} />
          </button>
        </div>

        {stats && stats.recent.length === 0 ? (
          <div className="p-12 text-center">
            <img src="https://images.pexels.com/photos/36123565/pexels-photo-36123565.jpeg" alt="Vuoto" className="mx-auto h-40 w-full max-w-md object-cover rounded-md opacity-90" />
            <p className="mt-5 font-display text-lg font-bold">Nessun ordine in attesa</p>
            <p className="text-sm text-muted-foreground mt-1">Incolla il tuo primo ordine e lascia che Voxera faccia il lavoro.</p>
            <button data-testid="empty-new-order" onClick={() => navigate("/app/new")} className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90">
              <Plus size={16} weight="bold" /> Nuovo Ordine
            </button>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {stats?.recent.map((o) => (
              <button
                key={o.id}
                data-testid={`recent-order-${o.id}`}
                onClick={() => navigate(`/app/orders/${o.id}`)}
                className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-secondary/50 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{o.customer_name || "Cliente sconosciuto"}</p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {o.line_items.length} articoli · {o.source_type}
                  </p>
                </div>
                <StatusBadge status={o.status} />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
