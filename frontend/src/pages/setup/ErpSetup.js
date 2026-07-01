import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack, Field, inputCls } from "./_shared";
import { StatusBadge } from "@/components/StatusBadge";
import { Plugs, Lightning } from "@phosphor-icons/react";

const FORMATS = ["json", "csv", "xml"];
const FUTURE = ["SAP", "Business Central", "Zucchetti", "TeamSystem", "Oracle", "Sage", "Odoo", "Dynamics 365"];

export default function ErpSetup() {
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/integrations/erp").then(({ data }) => setCfg({
    provider: data.provider || "webhook", format: data.format || "json",
    endpoint_url: data.endpoint_url || "", method: data.method || "POST",
    auth_header_name: data.auth_header_name || "", auth_header_value: data.auth_header_value || "",
    status: data.status || "not_configured", last_error: data.last_error,
  })).catch(() => {});
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setCfg({ ...cfg, [k]: e.target.value });

  const save = async () => {
    setBusy(true);
    try { await api.post("/integrations/erp", cfg); toast.success("Configurazione salvata"); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const test = async () => {
    if (!cfg.endpoint_url) return toast.error("Inserisci l'URL dell'endpoint.");
    setBusy(true);
    try {
      await api.post("/integrations/erp", cfg);
      await api.post("/integrations/erp/test");
      toast.success("Connessione ERP verificata ✅");
      load();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  if (!cfg) return null;

  return (
    <div className="animate-fade-up max-w-2xl">
      <SetupBack />
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-md bg-secondary flex items-center justify-center"><Plugs size={22} /></div>
          <div>
            <h1 className="font-display text-3xl font-black tracking-tighter">Export ERP</h1>
            <p className="text-sm text-muted-foreground">Architettura ERP-agnostica. Ogni ordine approvato esce in un formato standard.</p>
          </div>
        </div>
        {cfg.status !== "not_configured" && <StatusBadge status={cfg.status === "connected" ? "validated" : cfg.status === "error" ? "needs_review" : "ready"} />}
      </div>

      <div className="rounded-md border border-border bg-white p-6 space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Tipo connettore" testid="erp-provider">
            <select value={cfg.provider} onChange={set("provider")} className={inputCls}>
              <option value="webhook">Webhook</option>
              <option value="rest">REST API</option>
            </select>
          </Field>
          <Field label="Formato" testid="erp-format">
            <select value={cfg.format} onChange={set("format")} className={inputCls}>
              {FORMATS.map((f) => <option key={f} value={f}>{f.toUpperCase()}</option>)}
            </select>
          </Field>
        </div>
        <Field label="URL endpoint" hint="Dove Voxera invierà gli ordini approvati." testid="erp-url">
          <input value={cfg.endpoint_url} onChange={set("endpoint_url")} placeholder="https://erp.tuaazienda.com/api/orders" className={inputCls} />
        </Field>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Header di autenticazione (nome)" hint="Opzionale, es. X-Api-Key" testid="erp-auth-name">
            <input value={cfg.auth_header_name} onChange={set("auth_header_name")} className={inputCls} />
          </Field>
          <Field label="Valore" testid="erp-auth-value">
            <input value={cfg.auth_header_value} onChange={set("auth_header_value")} placeholder="••••••" className={inputCls} />
          </Field>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button data-testid="erp-save" onClick={save} disabled={busy} className="rounded-md border border-input bg-white px-5 py-2.5 text-sm font-medium hover:bg-secondary disabled:opacity-60">Salva</button>
        <button data-testid="erp-test" onClick={test} disabled={busy} className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
          <Lightning size={16} weight="fill" /> {busy ? "Test…" : "Salva e invia ordine di prova"}
        </button>
      </div>

      <div className="mt-8 rounded-md border border-border bg-white p-5">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground mb-3">Connettori dedicati in arrivo</p>
        <div className="flex flex-wrap gap-2">
          {FUTURE.map((f) => (
            <span key={f} className="rounded-full border border-border bg-secondary px-3 py-1 text-xs text-muted-foreground">{f}</span>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Ogni connettore è un modulo indipendente sopra lo stesso formato standard <code className="font-mono">voxera.order.v1</code>, così se ne aggiungono di nuovi senza toccare il resto del prodotto.
        </p>
      </div>
    </div>
  );
}
