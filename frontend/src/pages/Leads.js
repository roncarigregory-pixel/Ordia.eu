import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { Skeleton } from "@/components/ui/skeleton";
import { Users, Mail, Phone, Globe } from "lucide-react";

export default function Leads() {
  const { t, lang } = useI18n();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/leads").then(({ data }) => setData(data)).catch(() => setData({ items: [], total: 0 }));
  }, []);

  const items = data?.items || [];
  const fmtDate = (iso) => {
    try { return new Date(iso).toLocaleString(lang === "it" ? "it-IT" : "en-US", { dateStyle: "medium", timeStyle: "short" }); }
    catch { return iso; }
  };

  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">{t("Lead / Lista d'attesa")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("Persone interessate raccolte dalla landing (accesso anticipato).")}</p>
      </div>

      <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <Users size={16} /> <span data-testid="leads-total">{t("leads.total", { n: data?.total || 0 })}</span>
      </div>

      <div className="rounded-xl border border-border bg-white overflow-hidden">
        {!data ? (
          <div className="p-4 space-y-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12 rounded-md" />)}</div>
        ) : items.length === 0 ? (
          <div className="p-16 text-center text-sm text-muted-foreground">{t("Ancora nessun lead. Condividi la landing per iniziare a raccoglierli.")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Email")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden sm:table-cell">{t("Azienda")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden md:table-cell">{t("Telefono")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground hidden lg:table-cell">{t("Paese")}</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Data")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((l) => (
                <tr key={l.id} data-testid={`lead-row-${l.id}`} className="hover:bg-secondary/50 transition-colors">
                  <td className="px-5 py-3 font-medium"><span className="inline-flex items-center gap-2"><Mail size={14} className="text-slate-400" />{l.email}</span></td>
                  <td className="px-5 py-3 text-muted-foreground hidden sm:table-cell">{l.company_name || "—"}</td>
                  <td className="px-5 py-3 text-muted-foreground font-mono hidden md:table-cell">{l.phone ? <span className="inline-flex items-center gap-1.5"><Phone size={13} className="text-slate-400" />{l.phone}</span> : "—"}</td>
                  <td className="px-5 py-3 text-muted-foreground hidden lg:table-cell">{l.country ? <span className="inline-flex items-center gap-1.5"><Globe size={13} className="text-slate-400" />{l.country}</span> : "—"}</td>
                  <td className="px-5 py-3 text-muted-foreground tabular-nums">{fmtDate(l.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
