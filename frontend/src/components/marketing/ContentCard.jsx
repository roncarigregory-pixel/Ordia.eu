import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import {
  Check, CalendarClock, Send, Trash2, Image as ImageIcon, Loader2, Hash, Megaphone,
} from "lucide-react";

const STATUS_STYLE = {
  idea: "bg-slate-100 text-slate-600",
  draft: "bg-blue-50 text-blue-700",
  review: "bg-amber-50 text-amber-700",
  approved: "bg-violet-50 text-violet-700",
  scheduled: "bg-cyan-50 text-cyan-700",
  published: "bg-emerald-50 text-emerald-700",
};

const BACKEND = process.env.REACT_APP_BACKEND_URL;

// Reusable content card with the full Generate -> Review -> Approve -> Schedule -> Publish workflow.
export function ContentCard({ item, onChange }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState("");

  const act = async (key, fn) => {
    setBusy(key);
    try { await fn(); onChange && onChange(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(""); }
  };

  const approve = () => act("approve", () => api.post(`/marketing/content/${item.id}/approve`).then(() => toast.success(t("Approvato."))));
  const schedule = () => {
    const when = new Date(Date.now() + 24 * 3600 * 1000).toISOString();
    return act("schedule", () => api.post(`/marketing/content/${item.id}/schedule`, { scheduled_at: when }).then(() => toast.success(t("Programmato per domani."))));
  };
  const publish = () => act("publish", () => api.post(`/marketing/content/${item.id}/publish`).then(({ data }) => {
    toast.success(data?._delivery?.webhook_configured ? t("Pubblicato (inviato al webhook).") : t("Pubblicato. Configura un webhook per l'invio automatico."));
  }));
  const genImage = () => act("image", () => api.post(`/marketing/content/${item.id}/image`, {}).then(() => toast.success(t("Immagine generata."))));
  const del = () => act("delete", () => api.delete(`/marketing/content/${item.id}`).then(() => toast.success(t("Eliminato."))));

  return (
    <div data-testid={`mkt-card-${item.id}`} className="rounded-xl border border-border bg-white p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-xs font-medium capitalize">
            <Megaphone size={12} /> {item.channel?.replace(/_/g, " ")}
          </span>
          <span className="rounded-md bg-secondary px-2 py-0.5 text-xs text-muted-foreground capitalize">{item.category?.replace(/_/g, " ")}</span>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLE[item.status] || "bg-slate-100"}`}>{t(`status.${item.status}`)}</span>
      </div>

      {item.image_url && (
        <img src={`${BACKEND}${item.image_url}`} alt="" className="h-40 w-full rounded-lg object-cover" data-testid={`mkt-img-${item.id}`} />
      )}

      <h3 className="font-semibold text-sm leading-snug">{item.title || t("(senza titolo)")}</h3>
      {item.body && <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-5">{item.body}</p>}
      {item.hashtags?.length > 0 && (
        <div className="flex flex-wrap gap-1 text-xs text-ai"><Hash size={12} className="mt-0.5" />{item.hashtags.join(" ")}</div>
      )}
      {item.cta && <p className="text-xs font-medium text-foreground">→ {item.cta}</p>}
      {item.scheduled_at && <p className="text-xs text-cyan-700">{t("Programmato")}: {new Date(item.scheduled_at).toLocaleString()}</p>}

      <div className="mt-auto flex flex-wrap gap-1.5 pt-2 border-t border-border">
        {!item.image_url && (
          <button data-testid={`mkt-genimg-${item.id}`} onClick={genImage} disabled={!!busy} className="inline-flex items-center gap-1 rounded-md border border-input px-2.5 py-1.5 text-xs font-medium hover:bg-secondary disabled:opacity-50">
            {busy === "image" ? <Loader2 size={13} className="animate-spin" /> : <ImageIcon size={13} />} {t("Immagine")}
          </button>
        )}
        {["idea", "draft", "review"].includes(item.status) && (
          <button data-testid={`mkt-approve-${item.id}`} onClick={approve} disabled={!!busy} className="inline-flex items-center gap-1 rounded-md bg-violet-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">
            {busy === "approve" ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} {t("Approva")}
          </button>
        )}
        {["approved", "draft"].includes(item.status) && (
          <button data-testid={`mkt-schedule-${item.id}`} onClick={schedule} disabled={!!busy} className="inline-flex items-center gap-1 rounded-md border border-input px-2.5 py-1.5 text-xs font-medium hover:bg-secondary disabled:opacity-50">
            {busy === "schedule" ? <Loader2 size={13} className="animate-spin" /> : <CalendarClock size={13} />} {t("Programma")}
          </button>
        )}
        {["approved", "scheduled"].includes(item.status) && (
          <button data-testid={`mkt-publish-${item.id}`} onClick={publish} disabled={!!busy} className="inline-flex items-center gap-1 rounded-md bg-primary px-2.5 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
            {busy === "publish" ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} {t("Pubblica")}
          </button>
        )}
        <button data-testid={`mkt-delete-${item.id}`} onClick={del} disabled={!!busy} className="ml-auto inline-flex items-center gap-1 rounded-md border border-input px-2 py-1.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50">
          {busy === "delete" ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
        </button>
      </div>
    </div>
  );
}
