import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Sparkles, Package, ShoppingCart, RefreshCw } from "lucide-react";

export default function CustomerDetail() {
  const { name } = useParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [data, setData] = useState(null);
  const [reordering, setReordering] = useState(false);

  const load = useCallback(() => {
    api.get(`/customers/${encodeURIComponent(name)}`)
      .then(({ data }) => setData(data))
      .catch(() => { toast.error(t("Cliente non trovato")); navigate("/app/customers"); });
  }, [name, navigate, t]);

  useEffect(() => { load(); }, [load]);

  const handleReorder = async () => {
    setReordering(true);
    try {
      const { data } = await api.post(`/customers/${encodeURIComponent(name)}/reorder`);
      toast.success(t("cust.reorderCreated", { n: data.line_items }));
      navigate(`/app/orders/${data.id}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("Impossibile creare il riordino."));
    } finally {
      setReordering(false);
    }
  };

  if (!data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64 rounded-xl lg:col-span-2" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  const { customer, orders, insights } = data;

  return (
    <div className="animate-fade-up">
      <button data-testid="back-to-customers" onClick={() => navigate("/app/customers")} className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft size={16} /> {t("Clienti")}
      </button>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-lg font-bold text-primary-foreground">
          {customer.name.slice(0, 2).toUpperCase()}
        </div>
        <div className="min-w-0">
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight">{customer.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("cust.ordersVolume", { orders: customer.orders, vol: (customer.volume || 0).toFixed(2) })}
          </p>
        </div>
        <button
          data-testid="reorder-button"
          onClick={handleReorder}
          disabled={reordering}
          className="ml-auto flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          <RefreshCw size={16} className={reordering ? "animate-spin" : ""} />
          {reordering ? t("Creazione…") : t("Riordina prodotti abituali")}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-xl border border-border bg-white">
            <div className="flex items-center gap-2 border-b border-border px-5 py-4">
              <ShoppingCart size={16} className="text-slate-400" />
              <h2 className="font-display text-lg font-bold tracking-tight">{t("Storico ordini")}</h2>
            </div>
            <div className="divide-y divide-border">
              {orders.map((o) => (
                <button
                  key={o.id}
                  data-testid={`customer-order-${o.id}`}
                  onClick={() => navigate(`/app/orders/${o.id}`)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-secondary/50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{o.line_items.length} {t("articoli")} · {o.source_type}</p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {new Date(o.created_at).toLocaleString("it-IT", { day: "2-digit", month: "short", year: "numeric" })}
                    </p>
                  </div>
                  <StatusBadge status={o.status} />
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-ai/20 bg-ai-soft/50 p-5">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles size={16} className="text-ai" />
              <h2 className="font-display text-lg font-bold tracking-tight">{t("Insight AI")}</h2>
            </div>
            <ul className="space-y-2.5">
              {insights.map((ins, i) => (
                <li key={ins} data-testid={`insight-${i}`} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ai" /> {ins}
                </li>
              ))}
            </ul>
          </div>

          {customer.favorite_products?.length > 0 && (
            <div className="rounded-xl border border-border bg-white p-5">
              <div className="mb-3 flex items-center gap-2">
                <Package size={16} className="text-slate-400" />
                <h2 className="font-display text-lg font-bold tracking-tight">{t("Prodotti abituali")}</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {customer.favorite_products.map((p) => (
                  <span key={p} className="rounded-full bg-secondary px-3 py-1 text-sm font-medium">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
