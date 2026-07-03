import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { SetupBack, Field, inputCls } from "./_shared";
import { toast } from "sonner";
import {
  Radio, Plus, Trash, UploadSimple, CheckCircle, Copy, ArrowsClockwise, Cpu,
  GraduationCap, Circle, Lightning, PauseCircle, Notebook, WifiSlash,
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

function ReadinessPanel({ readiness }) {
  if (!readiness) return null;
  const pct = Math.round((readiness.score || 0) * 100);
  return (
    <div data-testid="bridge-readiness" className="mt-3 rounded-md bg-secondary p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-muted-foreground">Apprendimento del gestionale</span>
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
              {c.label}
              {c.detail && <span className="text-muted-foreground"> · {c.detail}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BridgeDiary({ diary }) {
  if (!diary || diary.length === 0) return null;
  return (
    <div data-testid="bridge-diary" className="mt-3 rounded-md border border-border bg-white p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Notebook size={15} className="text-ai" />
        <span className="text-xs font-semibold text-foreground">Diario del Bridge</span>
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

function AgentCard({ agent, profiles, readiness, diary, onChange, onDelete, onActivate, onPause }) {
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
            <MIcon size={12} weight="fill" /> {m.label}
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
        <div className="mt-3 rounded-md bg-secondary p-3">
          <p className="text-xs text-muted-foreground mb-1">Codice di accoppiamento (inseriscilo nell'agente Bridge):</p>
          <div className="flex items-center gap-2">
            <span data-testid={`bridge-pairing-code-${agent.id}`} className="font-mono text-2xl font-bold tracking-[0.3em]">{agent.pairing_code}</span>
            <button onClick={() => { navigator.clipboard?.writeText(agent.pairing_code); toast.success("Codice copiato"); }} className="text-slate-400 hover:text-foreground">
              <Copy size={16} />
            </button>
          </div>
        </div>
      )}
      <div className="mt-3 grid sm:grid-cols-2 gap-3">
        <Field label="Gestionale / ERP">
          <input className={inputCls} defaultValue={agent.erp_name || ""} placeholder="es. Danea, Business Central"
            onBlur={(e) => onChange(agent.id, { erp_name: e.target.value })} data-testid={`bridge-erp-${agent.id}`} />
        </Field>
        <Field label="Profilo di export">
          <select className={inputCls} defaultValue={agent.profile_id || ""} data-testid={`bridge-profile-select-${agent.id}`}
            onChange={(e) => onChange(agent.id, { profile_id: e.target.value })}>
            <option value="">— nessuno (JSON canonico) —</option>
            {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
      </div>

      {agent.paired && maturity !== "active" && <ReadinessPanel readiness={readiness} />}

      {agent.paired && <BridgeDiary diary={diary} />}

      {agent.paired && maturity === "learning" && (
        <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1.5">
          <GraduationCap size={14} className="text-ai" />
          Modalità apprendimento: gli ordini vengono inseriti come <b>bozze di prova</b>. Ti avviseremo quando sarà pronto a inserirli da solo.
        </p>
      )}

      {agent.paired && maturity === "ready" && (
        <div data-testid={`bridge-ready-banner-${agent.id}`} className="mt-3 flex items-center justify-between rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5">
          <span className="text-sm text-blue-700 flex items-center gap-1.5">
            <Lightning size={16} weight="fill" /> Il Bridge ha imparato — pronto a inserire gli ordini automaticamente.
          </span>
          <button data-testid={`bridge-activate-${agent.id}`} onClick={() => onActivate(agent.id)}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 shrink-0">
            Attiva inserimento automatico
          </button>
        </div>
      )}

      {agent.paired && maturity === "active" && (
        <div className="mt-3 flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <span className="text-sm text-emerald-700 flex items-center gap-1.5">
            <Lightning size={16} weight="fill" /> Inserimento automatico attivo — gli ordini approvati finiscono direttamente nel gestionale.
          </span>
          <button data-testid={`bridge-pause-${agent.id}`} onClick={() => onPause(agent.id)}
            className="flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 shrink-0">
            <PauseCircle size={15} /> Rimetti in apprendimento
          </button>
        </div>
      )}

      {agent.last_seen && <p className="mt-2 text-xs text-muted-foreground">Ultimo contatto: {new Date(agent.last_seen).toLocaleString("it-IT")}</p>}
    </div>
  );
}

export default function BridgeSetup() {
  const [agents, setAgents] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [adapters, setAdapters] = useState([]);
  const [masterData, setMasterData] = useState([]);
  const [readiness, setReadiness] = useState({});
  const [diary, setDiary] = useState({});
  const [proposed, setProposed] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

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
    api.get("/export-profiles").then(({ data }) => setProfiles(data)).catch(() => {});
    api.get("/bridge/jobs").then(({ data }) => setJobs(data)).catch(() => {});
    api.get("/bridge/adapters").then(({ data }) => setAdapters(data)).catch(() => {});
    api.get("/bridge/master-data").then(({ data }) => setMasterData(data)).catch(() => {});
  };
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, []);

  const activateAgent = async (id) => {
    try { await api.post(`/bridge/agents/${id}/activate`); toast.success("Inserimento automatico attivato"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  const pauseAgent = async (id) => {
    try { await api.post(`/bridge/agents/${id}/pause`); toast.success("Bridge rimesso in apprendimento"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const confirmAdapter = async (id) => {
    try { await api.post(`/bridge/adapters/${id}/confirm`); toast.success("ERP attivato — ora è disponibile per tutti i clienti"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const createAgent = async () => {
    try { await api.post("/bridge/agents", { name: "Ordia Bridge" }); toast.success("Agente creato — usa il codice per accoppiarlo"); load(); }
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
      toast.success("Profilo proposto dall'AI — rivedi e salva");
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
      toast.success("Profilo salvato"); setProposed(null); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="animate-fade-up max-w-4xl">
      <SetupBack />
      <div className="flex items-center gap-2">
        <Cpu size={26} className="text-ai" />
        <h1 className="font-display text-4xl font-black tracking-tighter">Ordia Bridge</h1>
      </div>
      <p className="mt-1 text-sm text-muted-foreground mb-8">
        Gli ordini approvati appaiono direttamente nel tuo gestionale. Installalo una volta: il Bridge <b>impara il tuo gestionale nel tempo</b> e ti avvisa quando è pronto a inserire gli ordini da solo.
      </p>

      {/* AI Template Builder */}
      <section className="mb-10">
        <h2 className="font-display text-lg font-bold tracking-tight mb-1">1 · Formato del tuo gestionale</h2>
        <p className="text-sm text-muted-foreground mb-4">Carica un file già importato con successo nel tuo ERP. L'AI ne apprende il formato.</p>

        <label data-testid="bridge-upload-sample" className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 bg-white px-4 py-8 text-sm text-muted-foreground hover:border-ai transition-colors">
          <UploadSimple size={18} />
          {analyzing ? "Analisi in corso…" : "Carica un file d'esempio (CSV, Excel, XML)"}
          <input type="file" accept=".csv,.xlsx,.xls,.xml" className="hidden" onChange={(e) => analyzeFile(e.target.files?.[0])} />
        </label>

        {proposed && (
          <div data-testid="bridge-proposed-profile" className="mt-4 rounded-md border border-border bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="font-display font-bold">{proposed.name || "Profilo proposto"}</p>
                <p className="text-xs text-muted-foreground">{proposed.erp_name} · {proposed.format?.toUpperCase()} · sep "{proposed.delimiter}" · dec "{proposed.decimal_separator}"</p>
              </div>
              <button data-testid="bridge-save-profile" onClick={saveProfile} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                <CheckCircle size={16} /> Approva e salva
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="py-2 pr-4">Colonna</th><th className="py-2">Campo Ordia</th></tr></thead>
                <tbody className="divide-y divide-border">
                  {(proposed.columns || []).map((c, i) => (
                    <tr key={i} data-testid={`bridge-col-${i}`}>
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
                <span><b>{p.name}</b> <span className="text-muted-foreground">· {p.erp_name} · {p.format?.toUpperCase()} · {p.columns?.length} colonne</span></span>
                <button onClick={() => api.delete(`/export-profiles/${p.id}`).then(load)} className="text-slate-400 hover:text-red-500"><Trash size={15} /></button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Agents */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-display text-lg font-bold tracking-tight">2 · Agenti Bridge</h2>
            <p className="text-sm text-muted-foreground">Installa l'agente su un dispositivo sempre acceso (NAS, mini-PC). Accoppialo col codice: entra in apprendimento e diventa autonomo quando è pronto.</p>
          </div>
          <button data-testid="bridge-create-agent" onClick={createAgent} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
            <Plus size={16} /> Nuovo agente
          </button>
        </div>
        <div className="space-y-3">
          {agents.length === 0
            ? <p className="text-sm text-muted-foreground rounded-md border border-dashed border-border p-6 text-center">Nessun agente. Creane uno per iniziare.</p>
            : agents.map((a) => <AgentCard key={a.id} agent={a} profiles={profiles} readiness={readiness[a.id]} diary={diary[a.id]} onChange={updateAgent} onDelete={deleteAgent} onActivate={activateAgent} onPause={pauseAgent} />)}
        </div>
      </section>

      {/* Learned ERPs (adapters) + master-data */}
      <section className="mb-10">
        <h2 className="font-display text-lg font-bold tracking-tight mb-1">3 · ERP appresi (self-learning)</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Il Bridge apprende un ERP nuovo da una dimostrazione. Conferma l'ordine di prova per attivarlo — poi ogni cliente sullo stesso ERP lo eredita.
        </p>
        {adapters.length === 0 ? (
          <p className="text-sm text-muted-foreground rounded-md border border-dashed border-border p-6 text-center">Nessun ERP appreso ancora.</p>
        ) : (
          <div className="space-y-2">
            {adapters.map((a) => (
              <div key={a.id} data-testid={`adapter-${a.id}`} className="flex items-center justify-between rounded-md border border-border bg-white px-4 py-3 text-sm">
                <div>
                  <b>{a.erp_guess || a.erp_key}</b>
                  <span className="text-muted-foreground"> · v{a.version} · conf {Math.round((a.confidence || 0) * 100)}%
                    {a.heal_count ? ` · auto-riparato ${a.heal_count}×` : ""}
                    {a.test_order_ref ? ` · ordine di prova ${a.test_order_ref}` : ""}</span>
                </div>
                {a.status === "active" ? (
                  <span data-testid={`adapter-status-${a.id}`} className="flex items-center gap-1 text-xs rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-600">
                    <CheckCircle size={13} weight="fill" /> Attivo
                  </span>
                ) : (
                  <button data-testid={`adapter-confirm-${a.id}`} onClick={() => confirmAdapter(a.id)}
                    className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90">
                    Conferma ordine di prova
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        {masterData.length > 0 && (
          <div data-testid="master-data-summary" className="mt-4 flex flex-wrap gap-2">
            {masterData.map((m) => (
              <span key={m.kind + m.erp_key} className="text-xs rounded-full bg-secondary px-3 py-1 text-muted-foreground">
                {m.count} {m.kind === "customer" ? "clienti" : m.kind === "product" ? "prodotti" : "IVA"} sincronizzati
              </span>
            ))}
          </div>
        )}
      </section>

      {/* Delivery log */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <ArrowsClockwise size={16} className="text-slate-400" />
          <h2 className="font-display text-lg font-bold tracking-tight">4 · Consegne recenti</h2>
        </div>
        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuna consegna ancora. Approva un ordine per metterlo in coda.</p>
        ) : (
          <div className="rounded-md border border-border bg-white overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-border">
                {jobs.slice(0, 15).map((j) => (
                  <tr key={j.id} data-testid={`bridge-job-${j.id}`}>
                    <td className="px-4 py-2.5 font-medium">{j.customer_name || "Cliente"}</td>
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
      </section>
    </div>
  );
}
