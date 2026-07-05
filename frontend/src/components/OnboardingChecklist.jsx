import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Rocket, CheckCircle2, Circle, ArrowRight, X, Building2, Loader2 } from "lucide-react";

const SECTORS = [
  "Alimentari / Food & Beverage", "Bevande", "Ortofrutta", "Carne e salumi",
  "Latticini e formaggi", "Ittico / Pesce", "Surgelati", "Ferramenta / Utensileria",
  "Farmaceutico / Parafarmacia", "Materiale edile", "Cancelleria / Ufficio", "Altro",
];

export function OnboardingChecklist() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [hidden, setHidden] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const load = useCallback(() => {
    api.get("/onboarding/status").then(({ data }) => setStatus(data)).catch(() => setStatus(null));
  }, []);
  useEffect(() => {
    load();
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [load]);

  if (hidden || !status || status.dismissed || status.all_done) return null;

  const steps = status.steps || [];
  const doneCount = steps.filter((s) => s.done).length;
  const pct = Math.round((doneCount / steps.length) * 100);

  const goToStep = (s) => {
    if (s.key === "profile") { setProfileOpen(true); return; }
    navigate(s.route);
  };
  const skipStep = async (key) => {
    try { const { data } = await api.post("/onboarding/skip-step", { step: key }); setStatus(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const dismiss = async () => {
    setHidden(true);
    try { await api.post("/onboarding/dismiss"); } catch { /* keep hidden anyway */ }
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        data-testid="onboarding-checklist"
        className="mb-8 overflow-hidden rounded-2xl border border-ai/20 bg-gradient-to-br from-ai/[0.06] to-white p-6 sm:p-7"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ai text-white">
              <Rocket size={20} />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight">{t("Prepariamo Ordia insieme")}</h2>
              <p className="mt-0.5 text-sm text-muted-foreground">{t("Pochi passaggi e sarai pronto a ricevere ordini automaticamente. Ci pensiamo passo dopo passo.")}</p>
            </div>
          </div>
          <button data-testid="onboarding-dismiss" onClick={dismiss} title={t("Nascondi")} className="rounded-lg p-1.5 text-slate-400 hover:bg-secondary hover:text-foreground">
            <X size={18} />
          </button>
        </div>

        {/* progress */}
        <div className="mt-5 mb-4">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="font-medium text-muted-foreground">{t("Avanzamento")}</span>
            <span data-testid="onboarding-progress" className="font-bold text-foreground">{doneCount}/{steps.length}</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-ai transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <ul className="space-y-2">
          {steps.map((s, i) => {
            const nextPending = steps.findIndex((x) => !x.done && !x.skipped);
            const isNext = i === nextPending;
            return (
              <li key={s.key} data-testid={`onboarding-step-${s.key}`}
                className={`flex items-center justify-between gap-3 rounded-xl border p-3 transition-colors ${s.done ? "border-emerald-100 bg-emerald-50/40" : isNext ? "border-ai/30 bg-white" : "border-border bg-white"}`}>
                <div className="flex items-center gap-3 min-w-0">
                  {s.done
                    ? <CheckCircle2 size={20} className="shrink-0 text-emerald-500" />
                    : <Circle size={20} className={`shrink-0 ${s.skipped ? "text-slate-300" : isNext ? "text-ai" : "text-slate-300"}`} />}
                  <div className="min-w-0">
                    <p className={`text-sm font-semibold ${s.done ? "text-emerald-800" : "text-foreground"}`}>
                      {t(s.label)}
                      {s.skipped && <span className="ml-2 text-xs font-normal text-muted-foreground">· {t("saltato")}</span>}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">{t(s.desc)}</p>
                  </div>
                </div>
                {!s.done && (
                  <div className="flex shrink-0 items-center gap-2">
                    {s.skippable && !s.skipped && (
                      <button data-testid={`onboarding-skip-${s.key}`} onClick={() => skipStep(s.key)} className="rounded-lg px-2 py-1.5 text-xs font-medium text-muted-foreground hover:bg-secondary">
                        {t("Salta")}
                      </button>
                    )}
                    <button data-testid={`onboarding-cta-${s.key}`} onClick={() => goToStep(s)}
                      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold ${isNext ? "bg-primary text-primary-foreground hover:bg-primary/90" : "border border-input bg-white hover:bg-secondary"}`}>
                      {s.skipped ? t("Riprova") : t("Vai")} <ArrowRight size={14} />
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </motion.div>

      <ProfileDialog open={profileOpen} onClose={() => setProfileOpen(false)} sectors={SECTORS}
        onSaved={() => { setProfileOpen(false); load(); }} />
    </>
  );
}

function ProfileDialog({ open, onClose, onSaved, sectors }) {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: "", sector: "", erp_name: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.get("/company").then(({ data }) => setForm({ name: data?.name || "", sector: data?.sector || "", erp_name: data?.erp_name || "" })).catch(() => {});
  }, [open]);

  const save = async () => {
    if (!form.name.trim()) return toast.error(t("Inserisci il nome dell'azienda."));
    if (!form.sector.trim()) return toast.error(t("Seleziona il settore."));
    if (!form.erp_name.trim()) return toast.error(t("Indica il gestionale che usi (o scrivi 'Nessuno')."));
    setSaving(true);
    try {
      await api.put("/company", { name: form.name.trim(), sector: form.sector.trim(), erp_name: form.erp_name.trim() });
      toast.success(t("Profilo azienda salvato"));
      onSaved?.();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose?.()}>
      <DialogContent className="sm:max-w-md" data-testid="onboarding-profile-dialog">
        <DialogHeader>
          <DialogTitle className="font-display tracking-tight flex items-center gap-2"><Building2 size={18} className="text-ai" /> {t("Profilo azienda")}</DialogTitle>
          <DialogDescription>{t("Bastano tre informazioni. Ci aiutano a preparare Ordia per il tuo settore.")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("Nome azienda")}</label>
            <input data-testid="profile-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="es. Fresh Foods Ingrosso" className="mt-1 w-full rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("Settore")}</label>
            <select data-testid="profile-sector" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} className="mt-1 w-full rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
              <option value="">{t("Seleziona…")}</option>
              {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("Gestionale utilizzato")}</label>
            <input data-testid="profile-erp" value={form.erp_name} onChange={(e) => setForm({ ...form, erp_name: e.target.value })} placeholder="es. Danea, Zucchetti, Business Central, Nessuno" className="mt-1 w-full rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          </div>
        </div>
        <DialogFooter>
          <button onClick={onClose} className="rounded-lg border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary">{t("Annulla")}</button>
          <button data-testid="profile-save" disabled={saving} onClick={save} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">
            {saving && <Loader2 size={15} className="animate-spin" />} {t("Salva")}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
