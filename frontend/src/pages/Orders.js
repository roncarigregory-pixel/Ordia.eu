import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, MagnifyingGlass, CaretRight } from "@phosphor-icons/react";

const FILTERS = [
  { key: "all", label: "Tutti" },
  { key: "needs_review", label: "Da Revisionare" },
  { key: "ready", label: "Pronti" },
  { key: "validated", label: "Validati" },
  { key: "exported", label: "Esportati" },
];

export default function Orders() {
  const [orders, setOrders] = useState(null);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/orders").then(({ data }) => setOrders(data)).catch(() => setOrders([]));
  }, []);

  const filtered = (orders || []).filter((o) => {
    if (filter !== "all" && o.status !== filter) return false;
    if (q && !(o.customer_name || "").toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="animate-fade-up">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-4xl font-black tracking-tighter">Ordini</h1>
          <p className="mt-1 text-sm text-muted-foreground">Tutti gli ordini in arrivo, estratti e pronti da verificare.</p>
        </div>
        <button
          data-testid="orders-new-order"
          onClick={() => navigate("/app/new")}
          className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus size={18} weight="bold" /> Nuovo Ordine
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
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            data-testid="orders-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Cerca cliente…"
            className="w-full rounded-md border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div className="rounded-md border border-border bg-white overflow-hidden">
        {!orders ? (
          <div className="p-4 space-y-3">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12 rounded-md" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center text-sm text-muted-foreground">Nessun ordine trovato.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Cliente</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden sm:table-cell">Articoli</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden md:table-cell">Sorgente</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Stato</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((o) => (
                <tr
                  key={o.id}
                  data-testid={`order-row-${o.id}`}
                  onClick={() => navigate(`/app/orders/${o.id}`)}
                  className="cursor-pointer hover:bg-secondary/50 transition-colors"
                >
                  <td className="px-5 py-3 font-medium">{o.customer_name || "Cliente sconosciuto"}</td>
                  <td className="px-5 py-3 text-muted-foreground font-mono hidden sm:table-cell">{o.line_items.length}</td>
                  <td className="px-5 py-3 text-muted-foreground hidden md:table-cell capitalize">{o.source_type}</td>
                  <td className="px-5 py-3"><StatusBadge status={o.status} /></td>
                  <td className="px-5 py-3 text-right"><CaretRight size={16} className="text-slate-300 inline" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
