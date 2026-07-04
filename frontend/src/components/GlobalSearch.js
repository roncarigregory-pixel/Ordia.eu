import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { MagnifyingGlass, Tray, Package, UserCircle, ArrowRight } from "@phosphor-icons/react";

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [res, setRes] = useState({ orders: [], products: [], customers: [] });
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { t } = useI18n();

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else { setQ(""); setRes({ orders: [], products: [], customers: [] }); }
  }, [open]);

  const search = useCallback(async (value) => {
    if (!value.trim()) return setRes({ orders: [], products: [], customers: [] });
    try {
      const { data } = await api.get(`/search?q=${encodeURIComponent(value)}`);
      setRes(data);
    } catch { /* ignore search errors */ }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(q), 180);
    return () => clearTimeout(t);
  }, [q, search]);

  const go = (path) => { setOpen(false); navigate(path); };
  const has = res.orders.length || res.products.length || res.customers.length;

  return (
    <>
      <button
        data-testid="global-search-trigger"
        onClick={() => setOpen(true)}
        className="flex w-full items-center gap-2 rounded-lg border border-border bg-secondary/50 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary"
      >
        <MagnifyingGlass size={16} />
        <span className="flex-1 text-left">{t("Cerca…")}</span>
        <kbd className="rounded border border-border bg-white px-1.5 py-0.5 text-[10px] font-mono">⌘K</kbd>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/40 backdrop-blur-sm pt-[12vh] px-4" onClick={() => setOpen(false)}>
          <div data-testid="global-search-panel" onClick={(e) => e.stopPropagation()} className="w-full max-w-xl rounded-xl border border-border bg-white shadow-2xl overflow-hidden animate-fade-up">
            <div className="flex items-center gap-3 border-b border-border px-4">
              <MagnifyingGlass size={18} className="text-muted-foreground" />
              <input
                ref={inputRef}
                data-testid="global-search-input"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("Cerca clienti, ordini, prodotti, SKU…")}
                className="w-full bg-transparent py-4 text-sm outline-none"
              />
              <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">ESC</kbd>
            </div>
            <div className="max-h-[50vh] overflow-y-auto p-2">
              {!q && <p className="px-3 py-6 text-center text-sm text-muted-foreground">{t("Digita per cercare in tutto Ordia.")}</p>}
              {q && !has && <p className="px-3 py-6 text-center text-sm text-muted-foreground">{t("search.noResults", { q })}</p>}

              {res.customers.length > 0 && <Section title={t("Clienti")} />}
              {res.customers.map((c) => (
                <Row key={c.name} testid={`search-customer-${c.name}`} icon={UserCircle} title={c.name} sub={`${c.orders} ${t("ordini")}`} onClick={() => go(`/app/customers/${encodeURIComponent(c.name)}`)} />
              ))}
              {res.orders.length > 0 && <Section title={t("Ordini")} />}
              {res.orders.map((o) => (
                <Row key={o.id} testid={`search-order-${o.id}`} icon={Tray} title={o.customer_name || t("Cliente sconosciuto")} sub={`${o.status} · ${o.id.slice(0, 8)}`} onClick={() => go(`/app/orders/${o.id}`)} />
              ))}
              {res.products.length > 0 && <Section title={t("Prodotti")} />}
              {res.products.map((p) => (
                <Row key={p.id} testid={`search-product-${p.id}`} icon={Package} title={p.name} sub={`${p.sku} · €${(p.price || 0).toFixed(2)}`} onClick={() => go(`/app/catalog`)} />
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const Section = ({ title }) => (
  <p className="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">{title}</p>
);

const Row = ({ icon: Icon, title, sub, onClick, testid }) => (
  <button data-testid={testid} onClick={onClick} className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-secondary">
    <Icon size={18} className="text-muted-foreground" />
    <div className="min-w-0 flex-1">
      <p className="truncate text-sm font-medium">{title}</p>
      <p className="truncate text-xs text-muted-foreground">{sub}</p>
    </div>
    <ArrowRight size={14} className="text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
  </button>
);
