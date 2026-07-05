import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

// Stepper: Ricevuto -> Confermato -> Inviato -> Consegnato
export function OrderTimeline({ status, delivered, t }) {
  const confirmed = status === "validated" || status === "exported";
  const sent = status === "exported";
  const steps = [
    { key: "received", label: t("Ricevuto"), done: status !== "processing", current: status === "processing" },
    { key: "confirmed", label: t("Confermato"), done: confirmed, current: status === "needs_review" || status === "ready" },
    { key: "sent", label: t("Inviato"), done: sent, current: status === "validated" },
    { key: "delivered", label: t("Consegnato"), done: delivered, current: sent && !delivered },
  ];
  return (
    <div data-testid="order-timeline" className="mb-5 flex items-center gap-1 overflow-x-auto rounded-xl border border-border bg-white px-4 py-3">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-1 shrink-0">
          <div className="flex items-center gap-2">
            <span className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold transition-colors",
              s.done ? "bg-emerald-500 text-white"
                : s.current ? "bg-ai text-white ring-4 ring-ai/15"
                : "bg-slate-100 text-slate-400"
            )}>
              {s.done ? <Check size={13} /> : i + 1}
            </span>
            <span className={cn("text-xs font-medium", s.done ? "text-emerald-700" : s.current ? "text-foreground" : "text-slate-400")}>{s.label}</span>
          </div>
          {i < steps.length - 1 && <div className={cn("mx-2 h-px w-8 md:w-14", s.done ? "bg-emerald-300" : "bg-slate-200")} />}
        </div>
      ))}
    </div>
  );
}
