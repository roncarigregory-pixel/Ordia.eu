import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack, Field, inputCls } from "./_shared";
import { StatusBadge } from "@/components/StatusBadge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  WhatsappLogo, CheckCircle, WarningCircle, ArrowRight, Copy, PaperPlaneTilt,
  ShieldCheck, Circle, ArrowClockwise, Trash,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

const PREREQS = [
  { t: "Account Meta Business", d: "Un profilo su business.facebook.com dove gestisci la tua azienda." },
  { t: "Business verificato", d: "La verifica business di Meta (documenti azienda) sblocca l'invio e limiti più alti." },
  { t: "Numero WhatsApp Business", d: "Un numero non ancora usato su un normale account WhatsApp, registrato nel Cloud API." },
  { t: "Token permanente (System User)", d: "Un Access Token di un System User con gli scope whatsapp_business_messaging e whatsapp_business_management." },
];

const STAGES = ["Verifica Access Token", "Verifica numero WhatsApp", "Verifica account WABA", "Controllo permessi"];

const ERRORS = [
  { c: "Token non valido / scaduto (190, 401)", f: "Rigenera un token permanente da un System User in Impostazioni Business → Utenti di sistema." },
  { c: "Permessi mancanti (10, 200, 403)", f: "Assegna al System User gli scope whatsapp_business_messaging e whatsapp_business_management e i task sulla WABA." },
  { c: "ID non trovato (404)", f: "Controlla Phone Number ID e WABA ID in WhatsApp Manager: sono numerici e diversi tra loro." },
  { c: "Numero non registrato (2388103)", f: "Completa la registrazione del numero nel Cloud API e la verifica business, poi riprova." },
];

export default function WhatsAppSetup() {
  const [step, setStep] = useState(0);
  const [account, setAccount] = useState(null);
  const [form, setForm] = useState({ label: "WhatsApp Business", access_token: "", phone_number_id: "", waba_id: "", app_secret: "" });
  const [validating, setValidating] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState(null);
  const [testTo, setTestTo] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/integrations/whatsapp").then(({ data }) => {
      if (data.length) {
        setAccount(data[0]);
        setStep(data[0].status === "connected" ? 4 : 2);
      }
    }).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const saveCreds = async () => {
    if (!form.access_token || !form.phone_number_id || !form.waba_id)
      return toast.error("Compila Access Token, Phone Number ID e WABA ID.");
    setBusy(true);
    try {
      const { data } = await api.post("/integrations/whatsapp", form);
      setAccount(data);
      setStep(2);
      runValidation(data.id);
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const runValidation = async (id) => {
    const accId = id || account?.id;
    if (!accId) return;
    setError(null);
    setValidating(true);
    setStage(0);
    const timer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 700);
    try {
      const { data } = await api.post(`/integrations/whatsapp/${accId}/validate`);
      clearInterval(timer);
      setStage(STAGES.length);
      const { data: fresh } = await api.get("/integrations/whatsapp");
      setAccount(fresh.find((a) => a.id === accId) || fresh[0]);
      if (data.status === "connected") {
        toast.success("Connessione WhatsApp attiva ✅");
        setTimeout(() => setStep(3), 600);
      } else {
        setError(data.message || "Verifica fallita.");
      }
    } catch (err) {
      clearInterval(timer);
      setError(formatApiError(err));
    } finally {
      setValidating(false);
    }
  };

  const sendTest = async () => {
    if (!testTo) return toast.error("Inserisci il numero destinatario (con prefisso, es. 39333…).");
    setBusy(true);
    try {
      await api.post(`/integrations/whatsapp/${account.id}/test-message`, { to: testTo });
      toast.success("Messaggio di prova inviato ✅");
      setStep(4);
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const removeAccount = async () => {
    await api.delete(`/integrations/whatsapp/${account.id}`);
    setAccount(null); setStep(0); setForm({ label: "WhatsApp Business", access_token: "", phone_number_id: "", waba_id: "", app_secret: "" });
    toast.success("Account rimosso");
  };

  const webhookUrl = `${BACKEND}/api/webhooks/whatsapp`;

  const Stepper = () => (
    <div className="flex items-center gap-2 mb-8">
      {["Prerequisiti", "Credenziali", "Verifica", "Test", "Fatto"].map((label, i) => (
        <div key={label} className="flex items-center gap-2">
          <div className={cn("flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium",
            i < step ? "bg-emerald-50 text-emerald-700" : i === step ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground")}>
            {i < step ? <CheckCircle size={14} weight="fill" /> : <span className="font-mono">{i + 1}</span>}
            {label}
          </div>
          {i < 4 && <div className={cn("h-px w-4", i < step ? "bg-emerald-300" : "bg-border")} />}
        </div>
      ))}
    </div>
  );

  return (
    <div className="animate-fade-up max-w-2xl">
      <SetupBack />
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-md bg-emerald-50 flex items-center justify-center"><WhatsappLogo size={24} weight="fill" className="text-emerald-600" /></div>
          <div>
            <h1 className="font-display text-3xl font-black tracking-tighter">WhatsApp Business</h1>
            <p className="text-sm text-muted-foreground">Connetti il tuo numero in pochi minuti, senza supporto tecnico esterno.</p>
          </div>
        </div>
        {account && <StatusBadge status={account.status === "connected" ? "validated" : account.status === "error" ? "needs_review" : "ready"} />}
      </div>

      <Stepper />

      {/* STEP 0 — Prerequisiti */}
      {step === 0 && (
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="font-display text-lg font-bold tracking-tight mb-1">Cosa ti serve</h2>
          <p className="text-sm text-muted-foreground mb-5">Prepara questi elementi in Meta Business. Ti guidiamo a trovare ogni valore nel passo successivo.</p>
          <div className="space-y-3">
            {PREREQS.map((p) => (
              <div key={p.t} className="flex items-start gap-3">
                <ShieldCheck size={20} className="text-emerald-500 mt-0.5 shrink-0" />
                <div><p className="text-sm font-medium">{p.t}</p><p className="text-sm text-muted-foreground">{p.d}</p></div>
              </div>
            ))}
          </div>
          <a href="https://business.facebook.com/settings/system-users" target="_blank" rel="noreferrer" className="mt-5 inline-block text-sm text-blue-600 underline underline-offset-4">Apri Meta Business Settings ↗</a>
          <div className="mt-6">
            <button data-testid="wa-start" onClick={() => setStep(1)} className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90">
              Ho tutto pronto <ArrowRight size={16} weight="bold" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 1 — Credenziali */}
      {step === 1 && (
        <div className="rounded-md border border-border bg-white p-6 space-y-4">
          <h2 className="font-display text-lg font-bold tracking-tight">Inserisci le credenziali Meta</h2>
          <Field label="Etichetta" hint="Un nome per riconoscere questo numero." testid="wa-label">
            <input value={form.label} onChange={set("label")} className={inputCls} />
          </Field>
          <Field label="Access Token permanente" hint="System User → Genera token, con scope whatsapp_business_messaging + management." testid="wa-token">
            <input value={form.access_token} onChange={set("access_token")} placeholder="EAAG…" className={cn(inputCls, "font-mono")} />
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Phone Number ID" hint="WhatsApp Manager → Numeri di telefono." testid="wa-phone-id">
              <input value={form.phone_number_id} onChange={set("phone_number_id")} placeholder="123456789012345" className={cn(inputCls, "font-mono")} />
            </Field>
            <Field label="WhatsApp Business Account ID" hint="Impostazioni Business → Account WhatsApp." testid="wa-waba-id">
              <input value={form.waba_id} onChange={set("waba_id")} placeholder="987654321098765" className={cn(inputCls, "font-mono")} />
            </Field>
          </div>
          <Field label="App Secret (opzionale)" hint="Per verificare la firma dei webhook in ingresso." testid="wa-app-secret">
            <input value={form.app_secret} onChange={set("app_secret")} placeholder="••••••" className={cn(inputCls, "font-mono")} />
          </Field>
          <div className="flex gap-2 pt-2">
            <button onClick={() => setStep(0)} className="rounded-md border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary">Indietro</button>
            <button data-testid="wa-save-creds" onClick={saveCreds} disabled={busy} className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
              Connetti e verifica <ArrowRight size={16} weight="bold" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2 — Verifica */}
      {step === 2 && (
        <div className="rounded-md border border-border bg-white p-6">
          <h2 className="font-display text-lg font-bold tracking-tight mb-4">Verifica connessione in tempo reale</h2>
          <div className="space-y-3">
            {STAGES.map((s, i) => (
              <div key={s} data-testid={`wa-stage-${i}`} className={cn("flex items-center gap-3 rounded-md border px-4 py-3",
                !validating && !error && i < stage ? "border-emerald-200 bg-emerald-50" :
                validating && i < stage ? "border-emerald-200 bg-emerald-50" :
                validating && i === stage ? "border-slate-300" :
                error && i >= stage ? "border-red-200 bg-red-50" : "border-border")}>
                {(!validating && i < stage) || (validating && i < stage)
                  ? <CheckCircle size={18} weight="fill" className="text-emerald-500" />
                  : validating && i === stage ? <div className="h-2 w-2 rounded-full bg-slate-900 animate-pulse" />
                  : error && i >= stage ? <WarningCircle size={18} weight="fill" className="text-red-500" />
                  : <Circle size={18} className="text-slate-300" />}
                <span className="text-sm font-medium">{s}</span>
              </div>
            ))}
          </div>

          {error && (
            <div data-testid="wa-error" className="mt-4 rounded-md border border-red-200 bg-red-50 p-4">
              <p className="text-sm font-medium text-red-800 flex items-center gap-2"><WarningCircle size={16} weight="fill" /> Connessione non riuscita</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
              <div className="mt-3 flex gap-2">
                <button data-testid="wa-retry" onClick={() => runValidation()} className="flex items-center gap-1.5 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90"><ArrowClockwise size={16} /> Riprova</button>
                <button onClick={() => setStep(1)} className="rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary">Modifica credenziali</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 3 — Test message */}
      {step === 3 && (
        <div className="rounded-md border border-border bg-white p-6 space-y-4">
          <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3">
            <CheckCircle size={18} weight="fill" className="text-emerald-500" />
            <span className="text-sm text-emerald-800">Connesso: <span className="font-medium">{account?.verified_name || account?.label}</span> {account?.display_phone_number ? `(${account.display_phone_number})` : ""}</span>
          </div>
          <h2 className="font-display text-lg font-bold tracking-tight">Invia un messaggio di prova</h2>
          <Field label="Numero destinatario" hint="Con prefisso internazionale, senza + (es. 39333xxxxxxx). Idealmente il tuo numero." testid="wa-test-to">
            <input value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="393331234567" className={cn(inputCls, "font-mono")} />
          </Field>
          <div className="flex gap-2">
            <button data-testid="wa-send-test" onClick={sendTest} disabled={busy} className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
              <PaperPlaneTilt size={16} weight="fill" /> {busy ? "Invio…" : "Invia test"}
            </button>
            <button onClick={() => setStep(4)} className="rounded-md border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary">Salta</button>
          </div>
        </div>
      )}

      {/* STEP 4 — Fatto */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-6 text-center">
            <CheckCircle size={40} weight="fill" className="mx-auto text-emerald-500" />
            <h2 className="mt-3 font-display text-xl font-black tracking-tight text-emerald-900">WhatsApp è connesso</h2>
            <p className="mt-1 text-sm text-emerald-700">Gli ordini in arrivo diventeranno automaticamente bozze nella tua Inbox.</p>
          </div>

          <div className="rounded-md border border-border bg-white p-6 space-y-4">
            <h3 className="font-display font-bold tracking-tight">Ricezione ordini (webhook)</h3>
            <p className="text-sm text-muted-foreground">Nella configurazione WhatsApp della tua app Meta, incolla questi valori come Callback URL e Verify Token, poi iscriviti al campo <code className="font-mono">messages</code>.</p>
            <Field label="Callback URL" testid="wa-webhook-url">
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded border border-border bg-secondary px-3 py-2 text-sm font-mono break-all">{webhookUrl}</code>
                <button onClick={() => { navigator.clipboard.writeText(webhookUrl); toast.success("Copiato"); }} className="rounded-md border border-input bg-white p-2 hover:bg-secondary"><Copy size={16} /></button>
              </div>
            </Field>
            <Field label="Verify Token" testid="wa-verify-token">
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded border border-border bg-secondary px-3 py-2 text-sm font-mono break-all">{account?.verify_token}</code>
                <button onClick={() => { navigator.clipboard.writeText(account?.verify_token); toast.success("Copiato"); }} className="rounded-md border border-input bg-white p-2 hover:bg-secondary"><Copy size={16} /></button>
              </div>
            </Field>
          </div>

          <div className="flex gap-2">
            <button data-testid="wa-back-to-test" onClick={() => setStep(3)} className="rounded-md border border-input bg-white px-4 py-2.5 text-sm font-medium hover:bg-secondary">Invia altro test</button>
            <button data-testid="wa-remove" onClick={removeAccount} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"><Trash size={16} /> Rimuovi</button>
          </div>
        </div>
      )}

      {/* Troubleshooting */}
      <div className="mt-8">
        <Accordion type="single" collapsible>
          <AccordionItem value="troubleshooting" className="border border-border rounded-md bg-white px-4">
            <AccordionTrigger className="text-sm font-medium" data-testid="wa-troubleshooting">Risoluzione problemi & errori comuni</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 pb-2">
                {ERRORS.map((e) => (
                  <div key={e.c} className="text-sm">
                    <p className="font-medium">{e.c}</p>
                    <p className="text-muted-foreground">{e.f}</p>
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
}
