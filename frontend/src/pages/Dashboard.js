import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sparkles, Plus, ArrowUpRight, Inbox, Bell, Users, AlertTriangle,
  Lightbulb, GraduationCap, CircleCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NOTIF_ICON = { review: Inbox, warning: AlertTriangle, learning: GraduationCap, insight: Lightbulb };
const NOTIF_TINT = {
  review: "bg-amber-50 text-amber-600",
  warning: "bg-red-50 text-red-500",
  learning: "bg-ai-soft text-ai",
  insight: "bg-emerald-50 text-emerald-600",
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/command-center").then(({ data }) => setData(data)).catch(() => setData(false));
  }, []);

  if (!data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-28 rounded-2xl" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-80 rounded-xl lg:col-span-2" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  const { today, to_review, recent_activity, notifications, recent_customers, totals } = data;
  const summary = today.total === 0
    ? "Nessun ordine ricevuto oggi. Incolla il primo e lascia lavorare Ordia."
    : `Oggi ${today.total} ${today.total === 1 ? "ordine" : "ordini"} · ${today.auto} in automatico · ${today.review} da revisionare.`;

  return (
    <div className="animate-fade-up">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="mb-8 rounded-2xl border border-border bg-white p-6 sm:p-8"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-ai-soft px-2.5 py-1 text-xs font-medium text-ai">
              <Sparkles size={13} /> Centro di Comando
            </span>
            <h1 data-testid="command-summary" className="mt-3 font-display text-2xl sm:text-3xl font-bold tracking-tight leading-snug">
              {summary}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {totals.orders} ordini totali · {totals.customers} clienti nel tuo spazio di lavoro.
            </p>
          </div>
          <button
            data-testid="dashboard-new-order"
            onClick={() => navigate("/app/new")}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Plus size={18} /> Nuovo Ordine
          </button>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column */}
        <div className="space-y-6 lg:col-span-2">
          {/* To review */}
          <div className="rounded-xl border border-border bg-white">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="font-display text-lg font-bold tracking-tight">Da revisionare</h2>
              <button data-testid="view-all-orders" onClick={() => navigate("/app/orders")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
                Tutti gli ordini <ArrowUpRight size={14} />
              </button>
            </div>
            {to_review.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
                <CircleCheck size={28} className="text-emerald-500" />
                <p className="font-medium">Tutto in ordine</p>
                <p className="text-sm text-muted-foreground">Nessun ordine attende la tua conferma.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {to_review.map((o) => (
                  <button
                    key={o.id}
                    data-testid={`review-order-${o.id}`}
                    onClick={() => navigate(`/app/orders/${o.id}`)}
                    className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-secondary/50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{o.customer_name || "Cliente sconosciuto"}</p>
                      <p className="truncate font-mono text-xs text-muted-foreground">{o.line_items.length} articoli · {o.source_type}</p>
                    </div>
                    <StatusBadge status={o.status} />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Recent activity */}
          <div className="rounded-xl border border-border bg-white">
            <div className="border-b border-border px-5 py-4">
              <h2 className="font-display text-lg font-bold tracking-tight">Attività recente</h2>
            </div>
            {recent_activity.length === 0 ? (
              <p className="px-5 py-10 text-center text-sm text-muted-foreground">Ancora nessun ordine.</p>
            ) : (
              <div className="divide-y divide-border">
                {recent_activity.map((o) => (
                  <button
                    key={o.id}
                    data-testid={`activity-order-${o.id}`}
                    onClick={() => navigate(`/app/orders/${o.id}`)}
                    className="flex w-full items-center justify-between px-5 py-3 text-left transition-colors hover:bg-secondary/50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{o.customer_name || "Cliente sconosciuto"}</p>
                      <p className="truncate font-mono text-xs text-muted-foreground">
                        {new Date(o.created_at).toLocaleDateString("it-IT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                    <StatusBadge status={o.status} />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* AI notifications */}
          <div className="rounded-xl border border-border bg-white">
            <div className="flex items-center gap-2 border-b border-border px-5 py-4">
              <Bell size={16} className="text-ai" />
              <h2 className="font-display text-lg font-bold tracking-tight">Notifiche AI</h2>
            </div>
            {notifications.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nessuna notifica.</p>
            ) : (
              <div className="space-y-2 p-4">
                {notifications.map((n, i) => {
                  const Icon = NOTIF_ICON[n.type] || Sparkles;
                  return (
                    <div key={`${n.type}-${i}`} data-testid={`notification-${i}`} className="flex items-start gap-3 rounded-lg bg-secondary/50 p-3">
                      <span className={cn("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg", NOTIF_TINT[n.type] || "bg-ai-soft text-ai")}>
                        <Icon size={15} />
                      </span>
                      <p className="text-sm leading-snug">{n.text}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recent customers */}
          <div className="rounded-xl border border-border bg-white">
            <div className="flex items-center gap-2 border-b border-border px-5 py-4">
              <Users size={16} className="text-slate-400" />
              <h2 className="font-display text-lg font-bold tracking-tight">Clienti recenti</h2>
            </div>
            {recent_customers.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nessun cliente ancora.</p>
            ) : (
              <div className="divide-y divide-border">
                {recent_customers.map((c) => (
                  <button
                    key={c.name}
                    data-testid={`customer-${c.name}`}
                    onClick={() => navigate(`/app/customers/${encodeURIComponent(c.name)}`)}
                    className="flex w-full items-center justify-between px-5 py-3 text-left transition-colors hover:bg-secondary/50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{c.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{c.orders} ordini · €{(c.volume || 0).toFixed(0)}</p>
                    </div>
                    <ArrowUpRight size={14} className="text-slate-300" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
