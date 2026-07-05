import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";

const inp = "w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring";

// Fully configurable brand profile — nothing Ordia-specific is hardcoded.
export function BrandSettings() {
  const { t } = useI18n();
  const [b, setB] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/marketing/brand").then(({ data }) => setB(data)).catch(() => {}); }, []);
  if (!b) return <div className="p-8 text-center text-sm text-muted-foreground"><Loader2 className="mx-auto animate-spin" /></div>;

  const set = (k) => (e) => setB({ ...b, [k]: e.target.value });
  const setList = (k) => (e) => setB({ ...b, [k]: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) });

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/marketing/brand", {
        company_name: b.company_name, website: b.website, industry: b.industry,
        products: b.products, target_audience: b.target_audience, tone_of_voice: b.tone_of_voice,
        logo_url: b.logo_url, brand_colors: b.brand_colors, languages: b.languages,
        marketing_goals: b.marketing_goals, ctas: b.ctas, publish_webhook_url: b.publish_webhook_url,
      });
      setB(data); toast.success(t("Profilo brand salvato."));
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const Field = ({ label, k, list, placeholder, textarea }) => (
    <label className="space-y-1 text-sm block">
      <span className="text-muted-foreground">{label}</span>
      {textarea
        ? <textarea data-testid={`brand-${k}`} value={b[k] || ""} onChange={set(k)} rows={2} className={inp} placeholder={placeholder} />
        : <input data-testid={`brand-${k}`} value={list ? (b[k] || []).join(", ") : (b[k] || "")} onChange={list ? setList(k) : set(k)} className={inp} placeholder={placeholder} />}
    </label>
  );

  return (
    <div data-testid="mkt-brand-settings" className="rounded-xl border border-border bg-white p-6 space-y-4 max-w-2xl">
      <h2 className="font-display text-lg font-bold">{t("Profilo Brand")}</h2>
      <p className="text-sm text-muted-foreground">{t("Tutto è configurabile: questa piattaforma non è legata a un brand specifico.")}</p>
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label={t("Nome azienda")} k="company_name" />
        <Field label={t("Sito web")} k="website" />
      </div>
      <Field label={t("Settore")} k="industry" />
      <Field label={t("Prodotti / Servizi")} k="products" textarea />
      <Field label={t("Pubblico target")} k="target_audience" textarea />
      <Field label={t("Tono di voce")} k="tone_of_voice" />
      <div className="grid sm:grid-cols-2 gap-4">
        <Field label={t("Colori brand (separati da virgola)")} k="brand_colors" list placeholder="#0f172a, #6366f1" />
        <Field label={t("Lingue (separate da virgola)")} k="languages" list placeholder="en, it" />
      </div>
      <Field label={t("Obiettivi marketing (separati da virgola)")} k="marketing_goals" list />
      <Field label={t("CTA (separate da virgola)")} k="ctas" list />
      <Field label={t("Webhook pubblicazione (n8n / Make)")} k="publish_webhook_url" placeholder="https://..." />
      <button data-testid="brand-save" onClick={save} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} {t("Salva profilo")}
      </button>
    </div>
  );
}
