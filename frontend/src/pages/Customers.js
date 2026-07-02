import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Users, ArrowUpRight } from "lucide-react";

export default function Customers() {
  const [customers, setCustomers] = useState(null);
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/customers").then(({ data }) => setCustomers(data)).catch(() => setCustomers([]));
  }, []);

  const filtered = useMemo(
    () => (customers || []).filter((c) => !q || c.name.toLowerCase().includes(q.toLowerCase())),
    [customers, q]
  );

  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">Clienti</h1>
        <p className="mt-1 text-sm text-muted-foreground">Storico ordini, volumi e prodotti abituali per ogni cliente.</p>
      </div>

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
                <ArrowUpRight size={16} className="text-slate-300 transition-colors group-hover:text-primary" />
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
