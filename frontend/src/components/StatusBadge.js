import { cn } from "@/lib/utils";

const STATUS = {
  needs_review: { label: "Da Revisionare", cls: "text-amber-700 bg-amber-50 border-amber-200" },
  ready: { label: "Pronto", cls: "text-blue-700 bg-blue-50 border-blue-200" },
  validated: { label: "Validato", cls: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  exported: { label: "Esportato", cls: "text-slate-600 bg-slate-100 border-slate-200" },
};

export function StatusBadge({ status, className }) {
  const s = STATUS[status] || STATUS.ready;
  return (
    <span
      data-testid={`status-badge-${status}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        s.cls,
        className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {s.label}
    </span>
  );
}
