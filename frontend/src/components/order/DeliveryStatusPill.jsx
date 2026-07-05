import { cn } from "@/lib/utils";

// Real-time delivery status of an order into the ERP (via Bridge).
export function DeliveryStatusPill({ delivery, t }) {
  if (!delivery) return null;
  const map = {
    none: { cls: "bg-slate-100 text-slate-500", dot: "bg-slate-300", label: t("Nessun Bridge collegato"), pulse: false },
    pending: { cls: "bg-amber-50 text-amber-700 border border-amber-200", dot: "bg-amber-400", label: t("In coda per il Bridge…"), pulse: true },
    claimed: { cls: "bg-blue-50 text-blue-700 border border-blue-200", dot: "bg-blue-400", label: t("Consegna nel gestionale in corso…"), pulse: true },
    delivered: { cls: "bg-emerald-50 text-emerald-700 border border-emerald-200", dot: "bg-emerald-500", label: t("Consegnato nel gestionale ✓"), pulse: false },
    failed: { cls: "bg-red-50 text-red-700 border border-red-200", dot: "bg-red-500", label: t("Consegna non riuscita"), pulse: false },
  };
  const m = map[delivery.status] || map.none;
  return (
    <span data-testid="delivery-status" className={cn("inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium", m.cls)}>
      <span className={cn("h-2 w-2 rounded-full", m.dot, m.pulse && "animate-pulse")} />
      {m.label}{delivery.status === "delivered" && delivery.mode === "shadow" ? ` (${t("simulazione")})` : ""}
    </span>
  );
}
