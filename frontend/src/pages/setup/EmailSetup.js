import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack, Field, inputCls } from "./_shared";
import { StatusBadge } from "@/components/StatusBadge";
import { EnvelopeSimple, Copy, Info } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

const PROVIDERS = [
  { key: "forwarding", label: "Indirizzo di inoltro Ordia" },
  { key: "gmail", label: "Gmail / Google Workspace" },
  { key: "m365", label: "Microsoft 365 / Outlook" },
  { key: "imap", label: "Altro (IMAP)" },
];

export default function EmailSetup() {
  const [tab, setTab] = useState("inbound");
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/integrations/email").then(({ data }) => setCfg({
    inbound_provider: data.inbound_provider || "forwarding",
    inbound_host: data.inbound_host || "", inbound_email: data.inbound_email || "", inbound_password: "",
    outbound_enabled: !!data.outbound_enabled, outbound_host: data.outbound_host || "",
    outbound_port: data.outbound_port || 587, outbound_email: data.outbound_email || "", outbound_password: "",
    status: data.status || "not_configured", forwarding_address: data.forwarding_address,
  })).catch(() => {});
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setCfg({ ...cfg, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const save = async () => {
    setBusy(true);
    try { await api.post("/integrations/email", cfg); toast.success("Configurazione salvata"); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const validate = async () => {
    setBusy(true);
    try {
      await api.post("/integrations/email", cfg);
      const { data } = await api.post("/integrations/email/validate");
      toast.success(data.mode === "forwarding" ? "Indirizzo di inoltro attivo" : "Connessione email verificata ✅");
      load();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const pollNow = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/integrations/email/poll");
      toast.success(`${data.orders_created} nuovi ordini importati dalla posta`);
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  if (!cfg) return null;
  const isForwarding = cfg.inbound_provider === "forwarding";

  return (
    <div className="animate-fade-up max-w-2xl">
      <SetupBack />
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-md bg-secondary flex items-center justify-center"><EnvelopeSimple size={22} /></div>
          <div>
            <h1 className="font-display text-3xl font-black tracking-tighter">Email</h1>
            <p className="text-sm text-muted-foreground">Un altro canale d'ordine, accanto a WhatsApp.</p>
          </div>
        </div>
        {cfg.status !== "not_configured" && <StatusBadge status={cfg.status === "connected" ? "validated" : cfg.status === "error" ? "needs_review" : "ready"} />}
      </div>

      <div className="inline-flex rounded-md border border-border bg-white p-1 mb-4">
        {["inbound", "outbound"].map((t) => (
          <button key={t} data-testid={`email-tab-${t}`} onClick={() => setTab(t)}
            className={cn("rounded px-4 py-1.5 text-sm font-medium transition-colors", tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>
            {t === "inbound" ? "Ricezione ordini" : "Invio email"}
          </button>
        ))}
      </div>

      {tab === "inbound" ? (
        <div className="rounded-md border border-border bg-white p-6 space-y-4">
          <Field label="Provider" testid="email-provider">
            <select value={cfg.inbound_provider} onChange={set("inbound_provider")} className={inputCls}>
              {PROVIDERS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
            </select>
          </Field>

          {isForwarding ? (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
              <div className="flex items-start gap-2">
                <Info size={18} className="text-blue-600 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-blue-900 font-medium">Inoltra i tuoi ordini a questo indirizzo</p>
                  <p className="text-xs text-blue-700 mt-1">Ordia leggerà corpo e allegati (PDF, Excel, CSV, immagini) e creerà l'ordine automaticamente.</p>
                  <div className="mt-3 flex items-center gap-2">
                    <code data-testid="forwarding-address" className="flex-1 rounded border border-blue-200 bg-white px-3 py-2 text-sm font-mono">{cfg.forwarding_address}</code>
                    <button onClick={() => { navigator.clipboard.writeText(cfg.forwarding_address); toast.success("Copiato"); }} className="rounded-md border border-blue-200 bg-white p-2 hover:bg-blue-100"><Copy size={16} /></button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {cfg.inbound_provider === "imap" && (
                <Field label="Server IMAP" hint="es. imap.tuoprovider.com" testid="email-host">
                  <input value={cfg.inbound_host} onChange={set("inbound_host")} className={inputCls} />
                </Field>
              )}
              <Field label="Indirizzo email" testid="email-address">
                <input type="email" value={cfg.inbound_email} onChange={set("inbound_email")} className={inputCls} />
              </Field>
              <Field label="Password" hint="Con la verifica in due passaggi usa una App Password dedicata." testid="email-password">
                <input type="password" value={cfg.inbound_password} onChange={set("inbound_password")} placeholder="••••••••" className={inputCls} />
              </Field>
            </>
          )}
        </div>
      ) : (
        <div className="rounded-md border border-border bg-white p-6 space-y-4">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input type="checkbox" data-testid="outbound-enabled" checked={cfg.outbound_enabled} onChange={set("outbound_enabled")} className="h-4 w-4" />
            Abilita invio (conferme ordine, richieste chiarimenti, notifiche)
          </label>
          {cfg.outbound_enabled && (
            <>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Server SMTP" testid="smtp-host"><input value={cfg.outbound_host} onChange={set("outbound_host")} placeholder="smtp.gmail.com" className={inputCls} /></Field>
                <Field label="Porta" testid="smtp-port"><input type="number" value={cfg.outbound_port} onChange={set("outbound_port")} className={inputCls} /></Field>
              </div>
              <Field label="Email mittente" testid="smtp-email"><input type="email" value={cfg.outbound_email} onChange={set("outbound_email")} className={inputCls} /></Field>
              <Field label="Password" testid="smtp-password"><input type="password" value={cfg.outbound_password} onChange={set("outbound_password")} placeholder="••••••••" className={inputCls} /></Field>
            </>
          )}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <button data-testid="email-save" onClick={save} disabled={busy} className="rounded-md border border-input bg-white px-5 py-2.5 text-sm font-medium hover:bg-secondary disabled:opacity-60">Salva</button>
        <button data-testid="email-validate" onClick={validate} disabled={busy} className="rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
          {busy ? "Verifica…" : "Salva e verifica connessione"}
        </button>
        {cfg.status === "connected" && !isForwarding && (
          <button data-testid="email-poll" onClick={pollNow} disabled={busy} className="rounded-md border border-input bg-white px-5 py-2.5 text-sm font-medium hover:bg-secondary disabled:opacity-60">
            Controlla ora la posta
          </button>
        )}
      </div>
    </div>
  );
}
