import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { SetupBack, Field, inputCls } from "./_shared";
import { toast } from "sonner";
import {
  Radio, Plus, Trash, UploadSimple, CheckCircle, Copy, ArrowsClockwise, Cpu,
  GraduationCap, Circle, Lightning, PauseCircle, Notebook, WifiSlash,
  ChartLineUp, PaperPlaneTilt, CaretDown, CaretRight,
  MapPin, ArrowClockwise, At, ShieldCheck, WarningCircle,
} from "@phosphor-icons/react";

const SOURCE_OPTIONS = [
  "sku", "product", "quantity", "unit", "unit_price", "line_total",
  "customer_name", "delivery_date", "notes", "order_id", "total", "currency",
];

const MATURITY = {
  unpaired: { label: "In attesa", cls: "bg-amber-50 text-amber-600", icon: Circle },
  learning: { label: "Apprendimento", cls: "bg-ai/10 text-ai", icon: GraduationCap },
  ready:    { label: "Pronto", cls: "bg-blue-50 text-blue-600", icon: Lightning },
  active:   { label: "Attivo", cls: "bg-emerald-50 text-emerald-600", icon: Lightning },
};

const OP_LABELS = {
  open_form: "Apri la schermata Nuovo ordine",
  add_line: "Aggiungi una riga",
  save: "Salva l'ordine",
  wait: "Attendi il caricamento",
};
const FIELD_LABELS = {
  customer_name: "Inserisci il Cliente",
  sku: "Inserisci l'Articolo (codice)",
  product: "Inserisci l'Articolo",
  quantity: "Inserisci la Quantità",
  delivery_date: "Inserisci la data di consegna",
  notes: "Inserisci le note",
};
function describeStep(step, t) {
  const op = step.op;
  if (op === "set_field") return FIELD_LABELS[step.field] ? t(FIELD_LABELS[step.field]) : t("bridge.setField", { f: step.field || "" }).trim();
  if (op === "click" || op === "select") {
    const name = step.locator?.value || step.locator?.name;
    return name ? t("bridge.click", { name }) : t("Clicca il pulsante");
  }
  return OP_LABELS[op] ? t(OP_LABELS[op]) : (step.desc || op);
}
function ProcedurePreview({ spec }) {
  const { t } = useI18n();
  const steps = [...(spec?.steps || [])].sort((a, b) => (a.seq || 0) - (b.seq || 0));
  if (steps.length === 0) return <p className="text-xs text-muted-foreground">{t("Nessuna procedura registrata.")}</p>;
  const loop = spec.line_loop;
  const rows = [];
  let loopOpen = false;
  steps.forEach((s) => {
    if (loop && s.seq === loop.start_seq) { loopOpen = true; rows.push({ type: "loop-start" }); }
    rows.push({ type: "step", step: s, indent: loopOpen });
    if (loop && s.seq === loop.end_seq) { loopOpen = false; rows.push({ type: "loop-end" }); }
  });
  return (
    <ol data-testid="procedure-preview" className="mt-1 space-y-1.5">
      {rows.map((r, i) => {
        if (r.type === "loop-start")
          return <li key="loop-start" className="text-xs font-semibold text-ai flex items-center gap-1.5"><ArrowsClockwise size={13} /> {t("Per ogni riga dell'ordine:")}</li>;
        if (r.type === "loop-end") return <li key="loop-end" className="text-xs text-muted-foreground pl-5">{t("— fine ciclo righe —")}</li>;
        return (
          <li key={`step-${r.step.seq}`} className={`flex items-start gap-2 text-xs text-foreground ${r.indent ? "pl-5" : ""}`}>
            <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full bg-secondary text-[10px] font-bold flex items-center justify-center text-muted-foreground">{r.step.seq}</span>
            <span>{describeStep(r.step, t)}</span>
          </li>
        );
      })}
    </ol>
  );
}
const KIND_LABEL = { desktop_uia: "Desktop", web_dom: "Web", file_import: "File", api: "API" };

const BACKEND = process.env.REACT_APP_BACKEND_URL;

async function downloadBridge() {
  try {
    const { data } = await api.get("/bridge/agent/download", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([data], { type: "application/zip" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "ordia-bridge.zip";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    toast.success("Download del Bridge avviato");
  } catch (e) {
    toast.error(formatApiError(e));
  }
}

function ReadinessPanel({ readiness }) {
  const { t } = useI18n();
  if (!readiness) return null;
  const pct = Math.round((readiness.score || 0) * 100);
  return (
    <div data-testid="bridge-readiness" className="mt-3 rounded-md bg-secondary p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-muted-foreground">{t("Apprendimento del gestionale")}</span>
        <span data-testid="bridge-readiness-pct" className="text-xs font-bold text-foreground">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-ai transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <ul className="mt-3 space-y-1.5">
        {(readiness.checklist || []).map((c) => (
          <li key={c.key} data-testid={`readiness-${c.key}`} className="flex items-start gap-2 text-xs">
            {c.done
              ? <CheckCircle size={15} weight="fill" className="text-emerald-500 shrink-0 mt-px" />
              : <Circle size={15} className="text-slate-300 shrink-0 mt-px" />}
            <span className={c.done ? "text-foreground" : "text-muted-foreground"}>
              {t(c.label)}
              {c.detail && <span className="text-muted-foreground"> · {t(c.detail)}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BridgeDiary({ diary }) {
  const { t } = useI18n();
  if (!diary || diary.length === 0) return null;
  return (
    <div data-testid="bridge-diary" className="mt-3 rounded-md border border-border bg-white p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Notebook size={15} className="text-ai" />
        <span className="text-xs font-semibold text-foreground">{t("Diario del Bridge")}</span>
      </div>
      <ul className="space-y-1.5 max-h-44 overflow-y-auto">
        {diary.slice(0, 8).map((e) => (
          <li key={e.id} data-testid={`diary-event-${e.id}`} className="flex items-start gap-2 text-xs">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-ai/60" />
            <span className="text-muted-foreground">
              <span className="text-foreground">{e.message}</span>
              <span className="block text-[10px] text-slate-400">{new Date(e.created_at).toLocaleString("it-IT")}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BridgeStatusStepper({ agent, t }) {
  const online = agent.paired && agent.status === "online" && agent.last_seen;
  const steps = [
    { key: "install", label: t("Installazione"), done: agent.paired, current: !agent.paired },
    { key: "connect", label: t("Connessione"), done: online, current: agent.paired && !online },
    { key: "connected", label: t("Collegato"), done: online, current: false },
  ];
  return (
    <div data-testid={`bridge-stepper-${agent.id}`} className="flex items-center gap-1">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-1">
          <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${s.done ? "bg-emerald-500 text-white" : s.current ? "bg-ai text-white ring-4 ring-ai/15" : "bg-slate-100 text-slate-400"}`}>{s.done ? "✓" : i + 1}</span>
          <span className={`text-xs font-medium ${s.done ? "text-emerald-700" : s.current ? "text-foreground" : "text-slate-400"}`}>{s.label}</span>
          {i < steps.length - 1 && <div className={`mx-1.5 h-px w-6 ${s.done ? "bg-emerald-300" : "bg-slate-200"}`} />}
        </div>
      ))}
    </div>
  );
}

function AgentCard({ agent, profiles, readiness, diary, onChange, onDelete, onActivate, onPause, onReload, simple }) {
  const { t } = useI18n();
  const [techEmail, setTechEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const codeExpired = agent.code_status === "expired";

  const downloadInstaller = async () => {
    try {
      const { data } = await api.get("/bridge/installer/windows");
      if (data.available && data.url) window.open(data.url, "_blank");
      else toast.info(t("L'installer di Ordia Bridge sarà disponibile a breve. Contatta l'assistenza per riceverlo."));
    } catch { toast.error(t("Download non riuscito, riprova.")); }
  };
  const regenerate = async () => {
    setRegenerating(true);
    try { await api.post(`/bridge/agents/${agent.id}/regenerate-code`); toast.success(t("Nuovo codice generato")); onReload?.(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setRegenerating(false); }
  };
  const sendInstructions = async () => {
    if (!techEmail.trim()) return toast.error(t("Inserisci l'email del destinatario."));
    setSending(true);
    try { await api.post(`/bridge/agents/${agent.id}/send-instructions`, { email: techEmail.trim() }); toast.success(`${t("Istruzioni inviate a")} ${techEmail.trim()}`); setTechEmail(""); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setSending(false); }
  };
  const verifyConnection = async () => {
    setVerifying(true);
    try {
      const { data } = await api.get("/bridge/agents");
      const me = (data || []).find((a) => a.id === agent.id);
      if (me?.status === "online" && me?.last_seen) toast.success(t("Bridge online e collegato ✓"));
      else toast.error(t("Il Bridge non risulta online. Controlla che il computer sia acceso e connesso a internet."));
      onReload?.();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setVerifying(false); }
  };
  const online = agent.status === "online" && agent.last_seen;
  const offline = agent.paired && agent.status === "offline";
  const maturity = agent.paired ? (agent.maturity || "learning") : "unpaired";
  const m = MATURITY[maturity] || MATURITY.unpaired;
  const MIcon = m.icon;
  return (
    <div data-testid={`bridge-agent-${agent.id}`} className="rounded-md border border-border bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio size={18} className={online ? "text-emerald-500" : "text-slate-300"} weight="fill" />
          <span className="font-display font-bold tracking-tight">{agent.name}</span>
          <span data-testid={`bridge-maturity-${agent.id}`} className={`flex items-center gap-1 text-xs rounded-full px-2 py-0.5 ${m.cls}`}>
            <MIcon size={12} weight="fill" /> {t(m.label)}
          </span>
          {offline && (
            <span data-testid={`bridge-offline-${agent.id}`} className="flex items-center gap-1 text-xs rounded-full bg-red-50 px-2 py-0.5 text-red-500">
              <WifiSlash size={12} weight="fill" /> Offline
            </span>
          )}
        </div>
        <button data-testid={`bridge-agent-delete-${agent.id}`} onClick={() => onDelete(agent.id)} className="text-slate-400 hover:text-red-500">
          <Trash size={16} />
        </button>
      </div>
      {!agent.paired && agent.pairing_code && (
        <div className="mt-4 space-y-4">
          <BridgeStatusStepper agent={agent} t={t} />
          <div className="grid sm:grid-cols-[1fr_auto] gap-4 items-start">
            <div className="space-y-4">
              <div>
                <p className="text-sm font-semibold">1 · {t("Scarica e installa")}</p>
                <p className="text-xs text-muted-foreground mb-2">{t("Doppio clic sul file scaricato e segui la procedura. Nessun comando, niente Docker.")}</p>
                <button data-testid={`bridge-download-${agent.id}`} onClick={downloadInstaller}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                  <UploadSimple size={16} className="rotate-180" /> {t("Scarica Ordia Bridge")}
                </button>
              </div>

              {/* Codice di collegamento — box evidente */}
              <div data-testid={`bridge-pairing-box-${agent.id}`} className={`rounded-xl border p-4 ${codeExpired ? "border-red-200 bg-red-50/60" : "border-ai/25 bg-ai/5"}`}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <p className="text-sm font-bold text-foreground">2 · {t("Il tuo codice di accoppiamento")}</p>
                  <span data-testid={`bridge-code-status-${agent.id}`} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${codeExpired ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-700"}`}>
                    {codeExpired ? <><WarningCircle size={12} weight="fill" /> {t("Scaduto")}</> : <><CheckCircle size={12} weight="fill" /> {t("Valido")}</>}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  {t("Questo codice serve per collegare il programma Ordia Bridge installato sul PC del tuo ufficio al tuo account Ordia. Inseriscilo durante l'installazione del Bridge.")}
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2">
                    <span data-testid={`bridge-pairing-code-${agent.id}`} className={`font-mono text-2xl font-bold tracking-[0.3em] ${codeExpired ? "text-slate-400 line-through" : ""}`}>{agent.pairing_code}</span>
                  </div>
                  <button data-testid={`bridge-copy-code-${agent.id}`} disabled={codeExpired} onClick={() => { navigator.clipboard?.writeText(agent.pairing_code); toast.success(t("Codice copiato")); }}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary disabled:opacity-50">
                    <Copy size={15} /> {t("Copia codice")}
                  </button>
                  <button data-testid={`bridge-regenerate-${agent.id}`} disabled={regenerating} onClick={regenerate}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary disabled:opacity-50">
                    <ArrowClockwise size={15} className={regenerating ? "animate-spin" : ""} /> {t("Rigenera codice")}
                  </button>
                </div>
                {codeExpired && (
                  <p className="mt-2 text-xs text-red-600">{t("Il codice è scaduto per sicurezza. Premi \"Rigenera codice\" per crearne uno nuovo.")}</p>
                )}
                <p className="mt-3 text-[11px] text-muted-foreground flex items-center gap-1">
                  <MapPin size={12} className="text-ai shrink-0" />
                  {t("Trovi sempre questo codice in: Ordia → Impostazioni → Collega Bridge.")}
                </p>

                {/* Invia istruzioni al tecnico */}
                <div className="mt-3 border-t border-border/60 pt-3">
                  <p className="text-xs font-semibold mb-1.5 flex items-center gap-1.5"><At size={13} className="text-ai" /> {t("Invia istruzioni al tecnico")}</p>
                  <div className="flex flex-wrap gap-2">
                    <input data-testid={`bridge-tech-email-${agent.id}`} type="email" value={techEmail} onChange={(e) => setTechEmail(e.target.value)}
                      placeholder={t("email del tecnico o collega")}
                      className="flex-1 min-w-[180px] rounded-lg border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                    <button data-testid={`bridge-send-instructions-${agent.id}`} disabled={sending} onClick={sendInstructions}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                      <PaperPlaneTilt size={15} /> {t("Invia")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex flex-col items-center gap-1 rounded-lg border border-border bg-white p-3 shrink-0">
              <QRCodeSVG value={`ORDIA-PAIR:${agent.pairing_code}`} size={104} data-testid={`bridge-qr-${agent.id}`} />
              <span className="text-[10px] text-muted-foreground">{t("Oppure scansiona il QR")}</span>
            </div>
          </div>
          <div data-testid={`bridge-waiting-${agent.id}`} className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5">
            <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-xs text-amber-700">{t("In attesa del collegamento… questa pagina si aggiorna da sola appena il Bridge si connette.")}</span>
          </div>
        </div>
      )}

      {agent.paired && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <BridgeStatusStepper agent={agent} t={t} />
          <button data-testid={`bridge-verify-${agent.id}`} disabled={verifying} onClick={verifyConnection}
            className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-1.5 text-xs font-semibold hover:bg-secondary disabled:opacity-50">
            <ShieldCheck size={14} className={verifying ? "animate-pulse" : "text-emerald-600"} /> {t("Verifica collegamento")}
          </button>
        </div>
      )}
      {!simple && (<div className="mt-3 grid sm:grid-cols-2 gap-3">
        <Field label={t("Gestionale / ERP")}>
          <input className={inputCls} defaultValue={agent.erp_name || ""} placeholder="es. Danea, Business Central"
            onBlur={(e) => onChange(agent.id, { erp_name: e.target.value })} data-testid={`bridge-erp-${agent.id}`} />
        </Field>
        <Field label={t("Profilo di export")}>
          <select className={inputCls} defaultValue={agent.profile_id || ""} data-testid={`bridge-profile-select-${agent.id}`}
            onChange={(e) => onChange(agent.id, { profile_id: e.target.value })}>
            <option value="">{t("— nessuno (JSON canonico) —")}</option>
            {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
      </div>)}
      {agent.paired && maturity !== "active" && <ReadinessPanel readiness={readiness} />}

      {agent.paired && !simple && <BridgeDiary diary={diary} />}

      {agent.paired && maturity === "learning" && (
        <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1.5">
          <GraduationCap size={14} className="text-ai" />
          {t("Modalità apprendimento: gli ordini vengono inseriti come")} <b>{t("bozze di prova")}</b>{t(". Ti avviseremo quando sarà pronto a inserirli da solo.")}
        </p>
      )}

      {agent.paired && maturity === "ready" && (
        <div data-testid={`bridge-ready-banner-${agent.id}`} className="mt-3 flex items-center justify-between rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5">
          <span className="text-sm text-blue-700 flex items-center gap-1.5">
            <Lightning size={16} weight="fill" /> {t("Il Bridge ha imparato — pronto a inserire gli ordini automaticamente.")}
          </span>
          <button data-testid={`bridge-activate-${agent.id}`} onClick={() => onActivate(agent.id)}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 shrink-0">
            {t("Attiva inserimento automatico")}
          </button>
        </div>
      )}

      {agent.paired && maturity === "active" && (
        <div className="mt-3 flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <span className="text-sm text-emerald-700 flex items-center gap-1.5">
            <Lightning size={16} weight="fill" /> {t("Inserimento automatico attivo — gli ordini approvati finiscono direttamente nel gestionale.")}
          </span>
          <button data-testid={`bridge-pause-${agent.id}`} onClick={() => onPause(agent.id)}
            className="flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 shrink-0">
            <PauseCircle size={15} /> {t("Rimetti in apprendimento")}
          </button>
        </div>
      )}

      {agent.last_seen && <p className="mt-2 text-xs text-muted-foreground">{t("Ultimo contatto:")} {new Date(agent.last_seen).toLocaleString("it-IT")}</p>}
    </div>
  );
}

export default function BridgeSetup() {
  const { t } = useI18n();
  const [agents, setAgents] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [adapters, setAdapters] = useState([]);
  const [masterData, setMasterData] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [diary, setDiary] = useState({});
  const [summary, setSummary] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [proposed, setProposed] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const hasPaired = agents.some((a) => a.paired);

  const load = () => {
    api.get("/bridge/agents").then(({ data }) => {
      setAgents(data);
      data.filter((a) => a.paired).forEach((a) => {
        api.get(`/bridge/agents/${a.id}/readiness`)
          .then(({ data: r }) => setReadiness((prev) => ({ ...prev, [a.id]: r })))
          .catch(() => {});
        api.get(`/bridge/agents/${a.id}/diary`)
          .then(({ data: d }) => setDiary((prev) => ({ ...prev, [a.id]: d })))
          .catch(() => {});
      });
    }).catch(() => {});
    api.get("/bridge/weekly-summary").then(({ data }) => setSummary(data)).catch(() => {});
    api.get("/export-profiles").then(({ data }) => setProfiles(data)).catch(() => {});
    api.get("/bridge/jobs").then(({ data }) => setJobs(data)).catch(() => {});
    api.get("/bridge/adapters").then(({ data }) => setAdapters(data)).catch(() => {});
    api.get("/bridge/master-data").then(({ data }) => setMasterData(data)).catch(() => {});
  };
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, []);

  const activateAgent = async (id) => {
    try { await api.post(`/bridge/agents/${id}/activate`); toast.success(t("Inserimento automatico attivato")); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const pauseAgent = async (id) => {
    try { await api.post(`/bridge/agents/${id}/pause`); toast.success(t("Bridge rimesso in apprendimento")); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const sendSummary = async () => {
    try { const { data } = await api.post("/bridge/weekly-summary/send", {}); toast.success(t("bridge.summarySent", { to: data.sent_to })); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const confirmAdapter = async (id) => {
    try { await api.post(`/bridge/adapters/${id}/confirm`); toast.success(t("ERP attivato — ora è disponibile per tutti i clienti")); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const createAgent = async () => {
    try { await api.post("/bridge/agents", { name: "Ordia Bridge" }); toast.success(t("Agente creato — usa il codice per accoppiarlo")); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const updateAgent = async (id, patch) => { try { await api.put(`/bridge/agents/${id}`, patch); load(); } catch (e) { toast.error(formatApiError(e)); } };
  const deleteAgent = async (id) => { try { await api.delete(`/bridge/agents/${id}`); load(); } catch (e) { toast.error(formatApiError(e)); } };

  const analyzeFile = async (file) => {
    if (!file) return;
    setAnalyzing(true); setProposed(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/export-profiles/analyze", fd);
      setProposed(data.proposed_profile);
      toast.success(t("Profilo proposto dall'AI — rivedi e salva"));
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setAnalyzing(false); }
  };

  const saveProfile = async () => {
    try {
      await api.post("/export-profiles", {
        name: proposed.name || "Profilo ERP", erp_name: proposed.erp_name || "",
        format: proposed.format || "csv", delimiter: proposed.delimiter || ",",
        decimal_separator: proposed.decimal_separator || ".", encoding: proposed.encoding || "UTF-8",
        has_header: proposed.has_header !== false,
        columns: (proposed.columns || []).map((c) => ({ header: c.header || c.source, source: c.source, transform: c.transform || null })),
      });
      toast.success(t("Profilo salvato")); setProposed(null); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="animate-fade-up max-w-4xl">
      <SetupBack />
      <div className="flex items-center gap-2">
        <Cpu size={26} className="text-ai" />
        <h1 className="font-display text-4xl font-black tracking-tighter">Ordia Bridge</h1>
      </div>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        {t("Il Bridge mette gli ordini approvati direttamente nel tuo gestionale. Si installa una volta sola su un computer vicino al gestionale. Segui i 3 passi qui sotto.")}
      </p>

      <button data-testid="bridge-toggle-advanced" onClick={() => setShowAdvanced((v) => !v)}
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
        {showAdvanced ? <CaretDown size={13} /> : <CaretRight size={13} />}
        {t("Impostazioni avanzate (formato ERP, ERP appresi, log)")}
      </button>

      {showAdvanced && summary && (summary.events_count > 0 || agents.some((a) => a.paired)) && (
        <div data-testid="bridge-weekly-summary" className="mb-8 rounded-md border border-border bg-white p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ChartLineUp size={18} className="text-ai" />
              <h2 className="font-display text-lg font-bold tracking-tight">{t("Il tuo Bridge questa settimana")}</h2>
            </div>
            <button data-testid="bridge-send-summary" onClick={sendSummary}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-semibold hover:bg-secondary">
              <PaperPlaneTilt size={15} /> {t("Inviami il riepilogo")}
            </button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { v: summary.drafts_prepared, l: t("bozze di prova corrette") },
              { v: summary.codes_in_catalog, l: t("codici in anagrafica") },
              { v: summary.self_heals, l: t("auto-riparazioni") },
            ].map((k) => (
              <div key={k.l} data-testid={`summary-metric-${k.l}`} className="rounded-md bg-secondary p-3 text-center">
                <div className="font-display text-2xl font-black text-foreground">{k.v}</div>
                <div className="text-xs text-muted-foreground">{k.l}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Template Builder (advanced) */}
      {showAdvanced && (<section className="mb-10">
        <h2 className="font-display text-lg font-bold tracking-tight mb-1">{t("Formato del tuo gestionale")}</h2>
        <p className="text-sm text-muted-foreground mb-4">{t("Carica un file già importato con successo nel tuo ERP. L'AI ne apprende il formato.")}</p>

        <label data-testid="bridge-upload-sample" className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 bg-white px-4 py-8 text-sm text-muted-foreground hover:border-ai transition-colors">
          <UploadSimple size={18} />
          {analyzing ? t("Analisi in corso…") : t("Carica un file d'esempio (CSV, Excel, XML)")}
          <input type="file" accept=".csv,.xlsx,.xls,.xml" className="hidden" onChange={(e) => analyzeFile(e.target.files?.[0])} />
        </label>

        {proposed && (
          <div data-testid="bridge-proposed-profile" className="mt-4 rounded-md border border-border bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="font-display font-bold">{proposed.name || t("Profilo proposto")}</p>
                <p className="text-xs text-muted-foreground">{proposed.erp_name} · {proposed.format?.toUpperCase()} · sep "{proposed.delimiter}" · dec "{proposed.decimal_separator}"</p>
              </div>
              <button data-testid="bridge-save-profile" onClick={saveProfile} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                <CheckCircle size={16} /> {t("Approva e salva")}
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="py-2 pr-4">{t("Colonna")}</th><th className="py-2">{t("Campo Ordia")}</th></tr></thead>
                <tbody className="divide-y divide-border">
                  {(proposed.columns || []).map((c, i) => (
                    <tr key={`${c.header || c.source}-${i}`} data-testid={`bridge-col-${i}`}>
                      <td className="py-2 pr-4 font-mono">{c.header || c.source}</td>
                      <td className="py-2">
                        <select className="rounded border border-input px-2 py-1 text-sm" defaultValue={c.source}
                          onChange={(e) => { const cols = [...proposed.columns]; cols[i] = { ...cols[i], source: e.target.value }; setProposed({ ...proposed, columns: cols }); }}>
                          {SOURCE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {profiles.length > 0 && (
          <div className="mt-4 space-y-2">
            {profiles.map((p) => (
              <div key={p.id} data-testid={`bridge-profile-${p.id}`} className="flex items-center justify-between rounded-md border border-border bg-white px-4 py-2.5 text-sm">
                <span><b>{p.name}</b> <span className="text-muted-foreground">· {p.erp_name} · {p.format?.toUpperCase()} · {p.columns?.length} {t("colonne")}</span></span>
                <button onClick={() => api.delete(`/export-profiles/${p.id}`).then(load)} className="text-slate-400 hover:text-red-500"><Trash size={15} /></button>
              </div>
            ))}
          </div>
        )}
      </section>)}

      {/* Agents — the simple connect flow (always visible) */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-display text-lg font-bold tracking-tight">{t("Collega il Bridge")}</h2>
            <p className="text-sm text-muted-foreground">{t("Crea il Bridge, poi installalo su un computer sempre acceso vicino al gestionale. Ti guidiamo passo passo.")}</p>
          </div>
          <button data-testid="bridge-create-agent" onClick={createAgent} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 shrink-0">
            <Plus size={16} /> {t("Nuovo Bridge")}
          </button>
        </div>

        {agents.length === 0 && (
          <div data-testid="bridge-empty-start" className="rounded-xl border border-dashed border-border bg-white p-8 text-center">
            <Cpu size={32} className="mx-auto text-ai mb-3" />
            <p className="font-semibold">{t("Nessun Bridge ancora")}</p>
            <p className="mt-1 text-sm text-muted-foreground mb-5">{t("Bastano pochi minuti. Clicca qui sotto per iniziare — ti diamo un codice e le istruzioni.")}</p>
            <button data-testid="bridge-start-big" onClick={createAgent} className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
              <Plus size={18} /> {t("Inizia: crea il Bridge")}
            </button>
          </div>
        )}

        <div className="space-y-3">
          {agents.map((a) => <AgentCard key={a.id} agent={a} profiles={profiles} readiness={readiness[a.id]} diary={diary[a.id]} onChange={updateAgent} onDelete={deleteAgent} onActivate={activateAgent} onPause={pauseAgent} onReload={load} simple={!showAdvanced} />)}
        </div>
      </section>

      {/* Learned ERPs (adapters) + master-data (advanced) */}
      {showAdvanced && (<section className="mb-10">
        <h2 className="font-display text-lg font-bold tracking-tight mb-1">{t("ERP appresi (self-learning)")}</h2>
        <p className="text-sm text-muted-foreground mb-4">
          {t("Il Bridge apprende un ERP nuovo da una dimostrazione. Conferma l'ordine di prova per attivarlo — poi ogni cliente sullo stesso ERP lo eredita.")}
        </p>
        {adapters.length === 0 ? (
          <p className="text-sm text-muted-foreground rounded-md border border-dashed border-border p-6 text-center">{t("Nessun ERP appreso ancora.")}</p>
        ) : (
          <div className="space-y-2">
            {adapters.map((a) => (
              <div key={a.id} data-testid={`adapter-${a.id}`} className="rounded-md border border-border bg-white px-4 py-3 text-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <b>{a.erp_guess || a.erp_key}</b>
                    <span data-testid={`adapter-kind-${a.id}`} className="text-[10px] font-semibold rounded-full bg-ai/10 px-2 py-0.5 text-ai">
                      {KIND_LABEL[a.adapter_kind] || "Web"}
                    </span>
                    <span className="text-muted-foreground text-xs">v{a.version} · conf {Math.round((a.confidence || 0) * 100)}%
                      {a.heal_count ? ` · auto-riparato ${a.heal_count}×` : ""}</span>
                  </div>
                  {a.status === "active" ? (
                    <span data-testid={`adapter-status-${a.id}`} className="flex items-center gap-1 text-xs rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-600">
                      <CheckCircle size={13} weight="fill" /> {t("Attivo")}
                    </span>
                  ) : (
                    <button data-testid={`adapter-confirm-${a.id}`} onClick={() => confirmAdapter(a.id)}
                      className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90">
                      {t("Conferma e attiva")}
                    </button>
                  )}
                </div>
                {(a.spec?.steps?.length > 0) && (
                  <div className="mt-2">
                    <button data-testid={`adapter-preview-toggle-${a.id}`}
                      onClick={() => setExpanded((p) => ({ ...p, [a.id]: !p[a.id] }))}
                      className="flex items-center gap-1 text-xs font-medium text-ai hover:underline">
                      {expanded[a.id] ? <CaretDown size={13} /> : <CaretRight size={13} />}
                      {t("bridge.stepsCount", { n: a.spec.steps.length })}
                    </button>
                    {expanded[a.id] && (
                      <div className="mt-2 rounded-md bg-secondary p-3">
                        {a.status !== "active" && (
                          <p className="text-xs text-muted-foreground mb-2">{t("Verifica cosa farà il Bridge, poi conferma per attivarlo.")}</p>
                        )}
                        <ProcedurePreview spec={a.spec} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {masterData.length > 0 && (
          <div data-testid="master-data-summary" className="mt-4 flex flex-wrap gap-2">
            {masterData.map((m) => (
              <span key={m.kind + m.erp_key} className="text-xs rounded-full bg-secondary px-3 py-1 text-muted-foreground">
                {m.count} {m.kind === "customer" ? t("clienti") : m.kind === "product" ? t("prodotti") : t("IVA")} {t("sincronizzati")}
              </span>
            ))}
          </div>
        )}
      </section>)}

      {/* Delivery log (advanced) */}
      {showAdvanced && (<section>
        <div className="flex items-center gap-2 mb-3">
          <ArrowsClockwise size={16} className="text-slate-400" />
          <h2 className="font-display text-lg font-bold tracking-tight">{t("Consegne recenti")}</h2>
        </div>
        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("Nessuna consegna ancora. Approva un ordine per metterlo in coda.")}</p>
        ) : (
          <div className="rounded-md border border-border bg-white overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-border">
                {jobs.slice(0, 15).map((j) => (
                  <tr key={j.id} data-testid={`bridge-job-${j.id}`}>
                    <td className="px-4 py-2.5 font-medium">{j.customer_name || t("Cliente")}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{j.erp_name || "—"}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${
                        j.status === "delivered" ? "bg-emerald-50 text-emerald-600"
                        : j.status === "exception" ? "bg-red-50 text-red-500"
                        : "bg-amber-50 text-amber-600"}`}>
                        {j.status === "delivered" ? "Consegnato" : j.status === "exception" ? "Errore" : j.status === "claimed" ? "In consegna" : "In coda"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>)}
    </div>
  );
}
