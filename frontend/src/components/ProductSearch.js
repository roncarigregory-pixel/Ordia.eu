import { useEffect, useMemo, useState, useRef } from "react";
import { Search, Check, X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/context/I18nContext";

export function ProductSearch({ products, value, onSelect, onCreate, invalid, testid }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef(null);
  const selected = products.find((p) => p.id === value);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const results = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const list = ql
      ? products.filter((p) =>
          p.name.toLowerCase().includes(ql) ||
          (p.sku || "").toLowerCase().includes(ql) ||
          (p.aliases || []).some((a) => a.toLowerCase().includes(ql)))
      : products;
    return list.slice(0, 40);
  }, [q, products]);

  const exactMatch = products.some((p) => p.name.toLowerCase() === q.trim().toLowerCase());

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        data-testid={testid}
        onClick={() => { setOpen((o) => !o); setQ(""); }}
        className={cn(
          "flex w-full items-center gap-2 rounded-lg border bg-white px-2.5 py-2 text-sm text-left transition-colors",
          invalid ? "border-amber-300" : "border-input hover:border-slate-300"
        )}
      >
        <span className={cn("flex-1 truncate", selected ? "text-foreground" : "text-amber-700")}>
          {selected ? selected.name : t("— Cerca prodotto —")}
        </span>
        {selected && <span className="shrink-0 font-mono text-xs text-muted-foreground">{selected.sku}</span>}
      </button>

      {open && (
        <div className="absolute z-30 mt-1 w-full min-w-[280px] rounded-xl border border-border bg-white shadow-lg">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={15} className="text-muted-foreground" />
            <input
              autoFocus
              data-testid={`${testid}-input`}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("Cerca per nome o SKU…")}
              className="w-full bg-transparent text-sm outline-none"
            />
          </div>
          <div className="max-h-64 overflow-y-auto p-1">
            {value && (
              <button
                onClick={() => { onSelect(null); setOpen(false); }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-red-500 hover:bg-red-50"
              >
                <X size={14} /> {t("Rimuovi abbinamento")}
              </button>
            )}
            {results.length === 0 && <p className="px-3 py-4 text-center text-sm text-muted-foreground">{t("Nessun prodotto.")}</p>}
            {results.map((p) => (
              <button
                key={p.id}
                data-testid={`product-option-${p.id}`}
                onClick={() => { onSelect(p.id); setOpen(false); }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left hover:bg-secondary"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{p.name}</p>
                  <p className="truncate font-mono text-xs text-muted-foreground">{p.sku} · €{(p.price || 0).toFixed(2)}/{p.unit}</p>
                </div>
                {p.id === value && <Check size={15} className="text-primary" />}
              </button>
            ))}
            {onCreate && q.trim() && !exactMatch && (
              <button
                data-testid={`${testid}-create`}
                onClick={() => { onCreate(q.trim()); setOpen(false); }}
                className="mt-1 flex w-full items-center gap-2 rounded-lg border-t border-border px-3 py-2.5 text-left text-ai hover:bg-ai-soft"
              >
                <Plus size={15} /> <span className="text-sm font-medium">{t("product.createNew", { q: q.trim() })}</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
