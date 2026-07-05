import { useCallback, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { ContentCard } from "@/components/marketing/ContentCard";
import { GeneratePanel } from "@/components/marketing/GeneratePanel";
import { BrandSettings } from "@/components/marketing/BrandSettings";
import {
  LayoutGrid, Sparkles, CalendarDays, Library, Palette, Loader2, Lightbulb, CalendarPlus,
} from "lucide-react";

const TABS = [
  { key: "overview", label: "Panoramica", icon: LayoutGrid },
  { key: "generate", label: "Genera", icon: Sparkles },
  { key: "calendar", label: "Calendario", icon: CalendarDays },
  { key: "library", label: "Libreria", icon: Library },
  { key: "brand", label: "Brand", icon: Palette },
];

const LIB_FILTERS = ["all", "idea", "draft", "approved", "scheduled", "published"];

export default function Marketing() {
  const { t } = useI18n();
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [recs, setRecs] = useState(null);
  const [content, setContent] = useState(null);
  const [filter, setFilter] = useState("all");
  const [calBusy, setCalBusy] = useState(false);

  const loadStats = useCallback(() => api.get("/marketing/stats").then(({ data }) => setStats(data)).catch(() => {}), []);
  const loadContent = useCallback((f) => {
    setContent(null);
    const params = f && f !== "all" ? { status: f } : {};
    return api.get("/marketing/content", { params }).then(({ data }) => setContent(data.items)).catch(() => setContent([]));
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { if (tab === "library" || tab === "calendar") loadContent(tab === "calendar" ? "all" : filter); }, [tab, filter, loadContent]);

  const loadRecs = () => {
    setRecs("loading");
    api.get("/marketing/recommendations").then(({ data }) => setRecs(data.ideas || [])).catch((e) => { setRecs([]); toast.error(formatApiError(e)); });
  };

  const genCalendar = async (period) => {
    setCalBusy(true);
    try {
      const { data } = await api.post("/marketing/calendar/generate", { period });
      toast.success(t("mkt.calGenerated", { n: data.count }));
      loadStats(); loadContent("all");
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setCalBusy(false); }
  };

  const refresh = () => { loadStats(); if (tab === "library") loadContent(filter); if (tab === "calendar") loadContent("all"); };

  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-ai/20 bg-ai-soft/60 px-3 py-1 text-xs font-medium text-ai mb-2">
          <Sparkles size={13} /> {t("AI Marketing Agent")}
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">{t("Marketing")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("Pianifica, genera, approva e programma contenuti su tutti i canali. Tu approvi sempre prima di pubblicare.")}</p>
      </div>

      <div className="mb-6 flex flex-wrap gap-1 border-b border-border">
        {TABS.map((tb) => (
          <button key={tb.key} data-testid={`mkt-tab-${tb.key}`} onClick={() => setTab(tb.key)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === tb.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            <tb.icon size={15} /> {t(tb.label)}
          </button>
        ))}
      </div>

      {/* OVERVIEW */}
      {tab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="mkt-stats">
            {["total", "idea", "draft", "approved", "scheduled", "published"].map((k) => (
              <div key={k} className="rounded-xl border border-border bg-white p-4">
                <div className="text-2xl font-bold tabular-nums">{stats ? (stats[k] ?? 0) : "—"}</div>
                <div className="text-xs text-muted-foreground capitalize">{t(k === "total" ? "Totale" : `status.${k}`)}</div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-border bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2"><Lightbulb className="text-amber-500" size={18} /><h2 className="font-semibold">{t("Raccomandazioni AI")}</h2></div>
              <button data-testid="mkt-load-recs" onClick={loadRecs} className="inline-flex items-center gap-2 rounded-lg border border-input px-3 py-1.5 text-sm font-medium hover:bg-secondary">
                {recs === "loading" ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {t("Suggerisci idee")}
              </button>
            </div>
            {recs === "loading" && <p className="text-sm text-muted-foreground">{t("Genero idee…")}</p>}
            {Array.isArray(recs) && recs.length === 0 && <p className="text-sm text-muted-foreground">{t("Clicca \"Suggerisci idee\" per ricevere spunti dall'AI.")}</p>}
            {Array.isArray(recs) && recs.length > 0 && (
              <ul className="space-y-3">
                {recs.map((r, i) => (
                  <li key={i} data-testid={`mkt-rec-${i}`} className="rounded-lg border border-border p-3">
                    <div className="flex items-center gap-2 text-sm font-medium">{r.title}
                      <span className="rounded bg-secondary px-1.5 py-0.5 text-xs text-muted-foreground capitalize">{(r.channel || "").replace(/_/g, " ")}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{r.why}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* GENERATE */}
      {tab === "generate" && <GeneratePanel onCreated={() => { toast.message(t("Trovi la bozza in Libreria.")); refresh(); }} />}

      {/* CALENDAR */}
      {tab === "calendar" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-white p-4 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium mr-2 inline-flex items-center gap-2"><CalendarPlus size={16} /> {t("Genera calendario bilanciato:")}</span>
            {["daily", "weekly", "monthly"].map((p) => (
              <button key={p} data-testid={`mkt-cal-${p}`} onClick={() => genCalendar(p)} disabled={calBusy}
                className="rounded-lg border border-input px-3 py-1.5 text-sm font-medium hover:bg-secondary disabled:opacity-50">
                {t(`period.${p}`)}
              </button>
            ))}
            {calBusy && <Loader2 size={16} className="animate-spin text-ai" />}
          </div>
          <ContentGrid content={content} onChange={refresh} emptyText={t("Nessun contenuto pianificato. Genera un calendario per iniziare.")} />
        </div>
      )}

      {/* LIBRARY */}
      {tab === "library" && (
        <div className="space-y-4">
          <div className="inline-flex flex-wrap gap-1 rounded-md border border-border bg-white p-1">
            {LIB_FILTERS.map((f) => (
              <button key={f} data-testid={`mkt-filter-${f}`} onClick={() => setFilter(f)}
                className={`rounded px-3 py-1.5 text-sm font-medium capitalize ${filter === f ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                {t(f === "all" ? "Tutti" : `status.${f}`)}
              </button>
            ))}
          </div>
          <ContentGrid content={content} onChange={refresh} emptyText={t("Nessun contenuto. Vai su \"Genera\" per crearne.")} />
        </div>
      )}

      {/* BRAND */}
      {tab === "brand" && <BrandSettings />}
    </div>
  );
}

function ContentGrid({ content, onChange, emptyText }) {
  if (content === null) return <div className="p-10 text-center"><Loader2 className="mx-auto animate-spin text-muted-foreground" /></div>;
  if (content.length === 0) return <div className="rounded-xl border border-dashed border-border p-12 text-center text-sm text-muted-foreground">{emptyText}</div>;
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="mkt-content-grid">
      {content.map((item) => <ContentCard key={item.id} item={item} onChange={onChange} />)}
    </div>
  );
}
