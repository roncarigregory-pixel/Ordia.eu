import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack } from "./_shared";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Skeleton } from "@/components/ui/skeleton";
import { Zap, ShieldCheck, UserPlus } from "lucide-react";

export default function AutomationSetup() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/automations").then(({ data }) => setCfg(data)).catch(() => setCfg(false));
  }, []);

  const set = (patch) => setCfg((c) => ({ ...c, ...patch }));

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/automations", {
        auto_confirm_enabled: cfg.auto_confirm_enabled,
        confidence_threshold: cfg.confidence_threshold,
        hold_new_customers: cfg.hold_new_customers,
      });
      setCfg(data);
      toast.success("Automazioni salvate");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-fade-up max-w-2xl">
      <SetupBack />
      <div className="mb-6 flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-ai-soft">
          <Zap size={22} className="text-ai" />
        </span>
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight">Automazioni</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">Lascia che Ordia confermi da sola gli ordini di cui è certa.</p>
        </div>
      </div>

      {cfg === null ? (
        <Skeleton className="h-72 rounded-xl" />
      ) : !cfg ? (
        <p className="text-sm text-muted-foreground">Impossibile caricare le automazioni.</p>
      ) : (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <ShieldCheck size={20} className="mt-0.5 text-primary" />
                <div>
                  <p className="font-semibold">Conferma automatica</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    Gli ordini con tutti gli articoli abbinati e ad alta confidenza vengono confermati
                    senza revisione manuale.
                  </p>
                </div>
              </div>
              <Switch
                data-testid="auto-confirm-switch"
                checked={cfg.auto_confirm_enabled}
                onCheckedChange={(v) => set({ auto_confirm_enabled: v })}
              />
            </div>

            {cfg.auto_confirm_enabled && (
              <div className="mt-5 border-t border-border pt-5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Soglia di confidenza minima</label>
                  <span data-testid="threshold-value" className="font-mono text-sm font-semibold text-ai">
                    {Math.round(cfg.confidence_threshold * 100)}%
                  </span>
                </div>
                <Slider
                  data-testid="threshold-slider"
                  className="mt-3"
                  min={50} max={100} step={5}
                  value={[Math.round(cfg.confidence_threshold * 100)]}
                  onValueChange={([v]) => set({ confidence_threshold: v / 100 })}
                />
                <p className="mt-2 text-xs text-muted-foreground">
                  Solo gli ordini in cui ogni articolo raggiunge questa confidenza saranno confermati automaticamente.
                </p>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-border bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <UserPlus size={20} className="mt-0.5 text-primary" />
                <div>
                  <p className="font-semibold">Trattieni i nuovi clienti</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    Il primo ordine di un cliente mai visto prima passa sempre dalla revisione manuale.
                  </p>
                </div>
              </div>
              <Switch
                data-testid="hold-new-switch"
                checked={cfg.hold_new_customers}
                onCheckedChange={(v) => set({ hold_new_customers: v })}
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              data-testid="save-automations-button"
              onClick={save}
              disabled={saving}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
            >
              {saving ? "Salvataggio…" : "Salva automazioni"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
