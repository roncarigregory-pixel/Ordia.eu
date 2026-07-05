import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Sparkles, Loader2, FileText } from "lucide-react";

const CHANNELS = ["linkedin", "twitter", "facebook", "instagram", "blog", "newsletter",
  "product_announcement", "video_script", "youtube_description", "short_form_idea",
  "carousel", "poll", "cta_variations"];
const CATEGORIES = ["product_updates", "customer_success", "industry_insights", "ai_automation",
  "erp_integrations", "order_management_tips", "behind_the_scenes", "founder_journey",
  "product_demos", "feature_highlights", "statistics", "faqs", "testimonials", "case_studies", "lead_generation"];

const sel = "w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring capitalize";

export function GeneratePanel({ onCreated }) {
  const { t } = useI18n();
  const [channel, setChannel] = useState("linkedin");
  const [category, setCategory] = useState("ai_automation");
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState("en");
  const [busy, setBusy] = useState(false);
  const [blogBusy, setBlogBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    try {
      await api.post("/marketing/generate", { channel, category, topic, language });
      toast.success(t("Bozza generata!"));
      onCreated && onCreated();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const generateBlog = async () => {
    if (!topic.trim()) return toast.error(t("Inserisci un argomento per il blog."));
    setBlogBusy(true);
    try {
      await api.post("/marketing/blog", { topic, language });
      toast.success(t("Articolo SEO generato!"));
      onCreated && onCreated();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBlogBusy(false); }
  };

  return (
    <div data-testid="mkt-generate-panel" className="rounded-xl border border-border bg-white p-6 space-y-4 max-w-2xl">
      <div className="flex items-center gap-2">
        <Sparkles className="text-ai" size={18} />
        <h2 className="font-display text-lg font-bold">{t("Genera contenuto AI")}</h2>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="space-y-1 text-sm">
          <span className="text-muted-foreground">{t("Canale")}</span>
          <select data-testid="mkt-gen-channel" value={channel} onChange={(e) => setChannel(e.target.value)} className={sel}>
            {CHANNELS.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-muted-foreground">{t("Categoria")}</span>
          <select data-testid="mkt-gen-category" value={category} onChange={(e) => setCategory(e.target.value)} className={sel}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
          </select>
        </label>
      </div>
      <label className="space-y-1 text-sm block">
        <span className="text-muted-foreground">{t("Argomento (opzionale)")}</span>
        <input data-testid="mkt-gen-topic" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t("es. come l'AI legge un ordine WhatsApp")} className="w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring" />
      </label>
      <label className="space-y-1 text-sm block max-w-[160px]">
        <span className="text-muted-foreground">{t("Lingua")}</span>
        <select data-testid="mkt-gen-language" value={language} onChange={(e) => setLanguage(e.target.value)} className={sel}>
          <option value="en">English</option>
          <option value="it">Italiano</option>
        </select>
      </label>
      <div className="flex flex-wrap gap-2 pt-1">
        <button data-testid="mkt-gen-submit" onClick={generate} disabled={busy || blogBusy} className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} {t("Genera contenuto")}
        </button>
        <button data-testid="mkt-gen-blog" onClick={generateBlog} disabled={busy || blogBusy} className="inline-flex items-center gap-2 rounded-lg border border-input px-5 py-2.5 text-sm font-medium hover:bg-secondary disabled:opacity-60">
          {blogBusy ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />} {t("Genera articolo SEO")}
        </button>
      </div>
    </div>
  );
}
