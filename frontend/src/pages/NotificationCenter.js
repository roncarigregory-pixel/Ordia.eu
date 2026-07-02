import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Ban, AlertTriangle, PackageX, XCircle, UserX, Mail, MessageCircle,
  FileText, MessageSquare, CheckCircle2, Search, ExternalLink, UserCheck, Archive, Check, Bell,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TYPE_ICON = {
  order_blocked: Ban, low_confidence: AlertTriangle, unrecognized_products: PackageX,
  erp_error: XCircle, export_error: XCircle, unknown_customer: UserX, new_email: Mail,
  new_whatsapp: MessageCircle, new_pdf: FileText, customer_request: MessageSquare, auto_confirmed: CheckCircle2,
};
const PRIORITY = {
  high: { dot: "bg-red-500", tint: "bg-red-50 text-red-600", label: "Alta" },
  medium: { dot: "bg-amber-500", tint: "bg-amber-50 text-amber-600", label: "Media" },
  low: { dot: "bg-emerald-500", tint: "bg-emerald-50 text-emerald-600", label: "Bassa" },
};
const TYPE_OPTIONS = [
  ["", "Tutti i tipi"], ["order_blocked", "Ordini bloccati"], ["low_confidence", "Confidenza bassa"],
  ["unrecognized_products", "Prodotti non riconosciuti"], ["unknown_customer", "Clienti sconosciuti"],
  ["erp_error", "Errori ERP"], ["new_email", "Nuove email"], ["new_whatsapp", "Nuovi WhatsApp"],
  ["new_pdf", "Nuovi documenti"], ["auto_confirmed", "Auto-confermati"],
];

function timeAgo(iso) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "adesso";
  if (s < 3600) return `${Math.floor(s / 60)} min fa`;
  if (s < 86400) return `${Math.floor(s / 3600)} h fa`;
  return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
}

export default function NotificationCenter() {
  const [items, setItems] = useState(null);
  const [counts, setCounts] = useState({ open: 0, high: 0, medium: 0, low: 0 });
  const [status, setStatus] = useState("open");
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const { user } = useAuth();
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (type) params.set("type", type);
    if (q) params.set("q", q);
    const [n, c] = await Promise.all([
      api.get(`/notifications?${params.toString()}`),
      api.get("/notifications/counts"),
    ]);
    setItems(n.data);
    setCounts(c.data);
  }, [status, type, q]);

  useEffect(() => { load().catch(() => setItems([])); }, [load]);
  useEffect(() => {
    const t = setInterval(() => load().catch(() => {}), 20000);
    return () => clearInterval(t);
  }, [load]);

  const patch = async (id, body, msg) => {
    try {
      await api.patch(`/notifications/${id}`, body);
      if (msg) toast.success(msg);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const STATUS_TABS = [["open", "Aperte"], ["resolved", "Risolte"], ["archived", "Archiviate"], ["", "Tutte"]];

  return (
    <div className="animate-fade-up">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">Centro Notifiche</h1>
          <p className="mt-1 text-sm text-muted-foreground">Il cuore operativo della tua giornata: tutto ciò che richiede attenzione, in tempo reale.</p>
        </div>
        <div className="flex items-center gap-2">
          {[["high", counts.high], ["medium", counts.medium], ["low", counts.low]].map(([p, n]) => (
            <div key={p} data-testid={`count-${p}`} className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium", PRIORITY[p].tint)}>
              <span className={cn("h-2 w-2 rounded-full", PRIORITY[p].dot)} /> {n} {PRIORITY[p].label}
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg border border-border bg-white p-0.5">
          {STATUS_TABS.map(([v, label]) => (
            <button
              key={v || "all"}
              data-testid={`status-tab-${v || "all"}`}
              onClick={() => setStatus(v)}
              className={cn("rounded-md px-3 py-1.5 text-sm font-medium transition-colors", status === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
            >
              {label}
            </button>
          ))}
        </div>
        <select data-testid="type-filter" value={type} onChange={(e) => setType(e.target.value)} className="rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
          {TYPE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input data-testid="notif-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca cliente…" className="w-full rounded-lg border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
        </div>
      </div>

      {/* List */}
      {!items ? (
        <div className="space-y-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-border bg-white p-16 text-center">
          <Bell size={32} className="mx-auto text-slate-300" />
          <p className="mt-3 font-medium">Nessuna notifica</p>
          <p className="text-sm text-muted-foreground">Tutto sotto controllo. Le nuove attività compaiono qui.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {items.map((n) => {
              const Icon = TYPE_ICON[n.type] || Bell;
              const pr = PRIORITY[n.priority] || PRIORITY.medium;
              return (
                <motion.div
                  key={n.id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, height: 0 }}
                  data-testid={`notification-card-${n.id}`}
                  className="flex items-start gap-4 rounded-xl border border-border bg-white p-4"
                >
                  <span className={cn("mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", pr.tint)}>
                    <Icon size={18} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn("h-2 w-2 rounded-full", pr.dot)} />
                      <p className="font-semibold">{n.title}</p>
                      {n.customer_name && <span className="text-sm text-muted-foreground">· {n.customer_name}</span>}
                      {n.status !== "open" && <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">{n.status === "resolved" ? "risolta" : "archiviata"}</span>}
                      <span className="ml-auto font-mono text-xs text-muted-foreground">{timeAgo(n.created_at)}</span>
                    </div>
                    {n.detail && <p className="mt-1 text-sm text-muted-foreground">{n.detail}</p>}
                    <div className="mt-2.5 flex flex-wrap items-center gap-2">
                      {n.suggested_action && (
                        <span className="rounded-md bg-ai-soft px-2 py-1 text-xs font-medium text-ai">Consigliato: {n.suggested_action}</span>
                      )}
                      {n.order_id && (
                        <button data-testid={`open-order-${n.id}`} onClick={() => navigate(`/app/orders/${n.order_id}`)} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1 text-xs font-medium hover:bg-secondary">
                          <ExternalLink size={13} /> Apri ordine
                        </button>
                      )}
                      {n.status === "open" && (
                        <>
                          <button data-testid={`assign-${n.id}`} onClick={() => patch(n.id, { assigned_to: user?.id }, "Assegnata a te")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1 text-xs font-medium hover:bg-secondary">
                            <UserCheck size={13} /> {n.assigned_to === user?.id ? "Tua" : "Assegna a me"}
                          </button>
                          <button data-testid={`resolve-${n.id}`} onClick={() => patch(n.id, { status: "resolved" }, "Segnata come risolta")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1 text-xs font-medium text-emerald-600 hover:bg-emerald-50">
                            <Check size={13} /> Risolvi
                          </button>
                          <button data-testid={`archive-${n.id}`} onClick={() => patch(n.id, { status: "archived" }, "Archiviata")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-secondary">
                            <Archive size={13} /> Archivia
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
