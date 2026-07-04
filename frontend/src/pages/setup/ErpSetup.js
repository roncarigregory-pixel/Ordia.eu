import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { SetupBack } from "./_shared";
import {
  Plug, Zap, Download, Trash2, Pencil, Plus, RefreshCw, CheckCircle2, XCircle, ArrowLeft, Boxes, Info, Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";

const FIELD_LABELS = {
  base_url: "URL di base", orders_endpoint: "Endpoint ordini (export)",
  catalog_endpoint: "Endpoint catalogo (import)", customers_endpoint: "Endpoint clienti (import)",
  auth_header_name: "Header autenticazione (nome)", auth_token: "Token / API key",
  database: "Database", company_db: "Company DB", tenant_id: "Tenant ID", environment: "Environment",
};
const MAP_FIELDS = [
  ["field_map", "Mapping campi ordine", '{"order_id": "external_ref"}'],
  ["product_map", "Mapping prodotti", '{"sku": "ItemCode", "name": "ItemName"}'],
  ["unit_map", "Mapping unità", '{"cassa": "BOX", "kg": "KG"}'],
  ["vat_map", "Mapping IVA (per SKU)", '{"PRD-001": 10}'],
  ["warehouse_map", "Mapping magazzini", '{"principale": "WH01"}'],
  ["pricelist_map", "Mapping listini", '{"default": "PL-STD"}'],
];
const STATUS_STYLE = {
  connected: "bg-emerald-50 text-emerald-600", configured: "bg-slate-100 text-slate-600",
  error: "bg-red-50 text-red-600",
};

export default function ErpSetup() {
  const [connectors, setConnectors] = useState([]);
  const [connections, setConnections] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [editing, setEditing] = useState(null); // connection draft or null
  const [busy, setBusy] = useState(false);
  const { t } = useI18n();

  const load = useCallback(async () => {
    const [c, conns, j] = await Promise.all([
      api.get("/erp/connectors"), api.get("/erp/connections"), api.get("/erp/jobs"),
    ]);
    setConnectors(c.data); setConnections(conns.data); setJobs(j.data);
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const startNew = (connectorType) => {
    const meta = connectors.find((c) => c.type === connectorType);
    setEditing({
      connector_type: connectorType, name: meta?.name || connectorType,
      config: Object.fromEntries((meta?.config_fields || []).map((f) => [f, ""])),
      mappings: {}, active: connections.length === 0, _fields: meta?.config_fields || [],
      _help: meta?.help || null, _hints: meta?.field_hints || {},
    });
  };

  const startEdit = (conn) => {
    const meta = connectors.find((c) => c.type === conn.connector_type);
    setEditing({ ...conn, config: { ...conn.config }, _fields: meta?.config_fields || Object.keys(conn.config || {}),
      _help: meta?.help || null, _hints: meta?.field_hints || {} });
  };

  const save = async () => {
    setBusy(true);
    try {
      const payload = { connector_type: editing.connector_type, name: editing.name, config: editing.config, mappings: editing.mappings || {}, active: editing.active };
      if (editing.id) await api.put(`/erp/connections/${editing.id}`, payload);
      else await api.post("/erp/connections", payload);
      toast.success(t("Connessione salvata"));
      setEditing(null); load();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const testConn = async (id) => {
    setBusy(true);
    try { const { data } = await api.post(`/erp/connections/${id}/test`); toast.success(t("erp.testOk", { status: data.status })); load(); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const doImport = async (id, resource) => {
    setBusy(true);
    try { const { data } = await api.post(`/erp/connections/${id}/import?resource=${resource}`); toast.success(resource === "catalog" ? t("erp.importedProducts", { n: data.imported }) : t("erp.importedCustomers", { n: data.imported })); }
    catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  const remove = async (id) => {
    if (!window.confirm(t("Eliminare questa connessione?"))) return;
    await api.delete(`/erp/connections/${id}`); toast.success(t("Connessione eliminata")); load();
  };

  const retryJob = async (id) => {
    try { await api.post(`/erp/jobs/${id}/retry`); toast.success(t("Retry avviato")); load(); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  // ---- Edit form ----
  if (editing) {
    const setCfg = (k, v) => setEditing((e) => ({ ...e, config: { ...e.config, [k]: v } }));
    const setMap = (k, v) => setEditing((e) => ({ ...e, mappings: { ...e.mappings, [`_raw_${k}`]: v } }));
    const commitMaps = () => {
      const out = { ...editing.mappings };
      for (const [k] of MAP_FIELDS) {
        const raw = editing.mappings[`_raw_${k}`];
        if (raw !== undefined) {
          try { out[k] = raw.trim() ? JSON.parse(raw) : {}; delete out[`_raw_${k}`]; }
          catch { throw new Error(`JSON non valido in "${k}"`); }
        }
      }
      return out;
    };
    const onSave = () => {
      try { const m = commitMaps(); setEditing((e) => ({ ...e, mappings: m })); setTimeout(save, 0); }
      catch (err) { toast.error(err.message); }
    };
    return (
      <div className="animate-fade-up max-w-2xl">
        <button onClick={() => setEditing(null)} className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft size={16} /> {t("Connettori")}</button>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight mb-1">{editing.id ? t("Modifica") : t("Configura")} · {editing.name}</h1>
        <p className="text-sm text-muted-foreground mb-6">{t("Ogni connettore è un modulo indipendente sopra il formato standard")} <code className="font-mono text-xs">ordia.order.v1</code>.</p>

        {editing._help && (
          <div data-testid="connector-wizard-help" className="mb-5 rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
            <div className="flex items-start gap-2">
              <Info size={16} className="mt-0.5 shrink-0 text-primary" />
              <p className="text-sm text-foreground">{editing._help.intro}</p>
            </div>
            {editing._help.ask_vendor && (
              <div className="rounded-lg bg-white/70 p-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{t("Cosa chiedere al fornitore")}</p>
                <p className="text-sm text-foreground">{editing._help.ask_vendor}</p>
              </div>
            )}
            {editing._help.no_api && (
              <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3">
                <Lightbulb size={15} className="mt-0.5 shrink-0 text-amber-500" />
                <p className="text-sm text-amber-700">{editing._help.no_api}</p>
              </div>
            )}
          </div>
        )}

        <div className="rounded-xl border border-border bg-white p-5 space-y-4">
          <div>
            <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Nome connessione")}</label>
            <input data-testid="conn-name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className="mt-1.5 w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring" />
          </div>
          {editing._fields.map((f) => (
            <div key={f}>
              <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t(FIELD_LABELS[f] || f)}</label>
              <input
                data-testid={`conn-${f}`}
                type={f === "auth_token" ? "password" : "text"}
                value={editing.config[f] || ""}
                onChange={(e) => setCfg(f, e.target.value)}
                placeholder={f === "auth_token" ? "••••••" : f.includes("endpoint") || f === "base_url" ? "https://…" : ""}
                className="mt-1.5 w-full rounded-lg border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              {editing._hints?.[f] && <p className="mt-1 text-xs text-muted-foreground">{editing._hints[f]}</p>}
            </div>
          ))}
          <label className="flex items-center gap-2 text-sm">
            <input data-testid="conn-active" type="checkbox" checked={editing.active} onChange={(e) => setEditing({ ...editing, active: e.target.checked })} className="h-4 w-4 rounded border-input" />
            {t("Connessione attiva (riceve gli export automatici)")}
          </label>
        </div>

        <details className="mt-4 rounded-xl border border-border bg-white p-5">
          <summary className="cursor-pointer text-sm font-semibold">{t("Mapping avanzato (campi, prodotti, unità, IVA, magazzini, listini)")}</summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {MAP_FIELDS.map(([k, label, ph]) => (
              <div key={k}>
                <label className="text-xs font-medium text-muted-foreground">{t(label)}</label>
                <textarea
                  data-testid={`map-${k}`}
                  rows={2}
                  defaultValue={JSON.stringify(editing.mappings?.[k] || {}, null, 0).replace("{}", "")}
                  onChange={(e) => setMap(k, e.target.value)}
                  placeholder={ph}
                  className="mt-1 w-full resize-none rounded-lg border border-input bg-white px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            ))}
          </div>
        </details>

        <div className="mt-4 flex gap-2">
          <button onClick={() => setEditing(null)} className="rounded-lg border border-input bg-white px-5 py-2.5 text-sm font-medium hover:bg-secondary">{t("Annulla")}</button>
          <button data-testid="save-connection" onClick={onSave} disabled={busy} className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60">{busy ? t("Salvataggio…") : t("Salva connessione")}</button>
        </div>
      </div>
    );
  }

  // ---- Main view ----
  return (
    <div className="animate-fade-up max-w-4xl">
      <SetupBack />
      <div className="mb-6 flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-secondary"><Plug size={22} /></span>
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight">{t("Integrazioni ERP")}</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{t("Architettura ERP-first modulare. Nessun ordine va perso: gli export falliti restano in coda e sono riprovabili.")}</p>
        </div>
      </div>

      {/* Active connections */}
      {connections.length > 0 && (
        <div className="mb-8 space-y-3">
          {connections.map((c) => (
            <div key={c.id} data-testid={`connection-${c.id}`} className="rounded-xl border border-border bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary text-sm font-bold">{c.name.slice(0, 2).toUpperCase()}</span>
                  <div>
                    <p className="font-semibold flex items-center gap-2">{c.name}
                      {c.active && <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">{t("attiva")}</span>}
                    </p>
                    <p className="text-xs text-muted-foreground">{connectors.find((k) => k.type === c.connector_type)?.name || c.connector_type}</p>
                  </div>
                </div>
                <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", STATUS_STYLE[c.status] || STATUS_STYLE.configured)}>{c.status}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button data-testid={`test-${c.id}`} onClick={() => testConn(c.id)} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"><Zap size={13} /> Testa</button>
                <button data-testid={`import-catalog-${c.id}`} onClick={() => doImport(c.id, "catalog")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"><Boxes size={13} /> Importa catalogo</button>
                <button data-testid={`import-customers-${c.id}`} onClick={() => doImport(c.id, "customers")} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"><Download size={13} /> Importa clienti</button>
                <button data-testid={`edit-${c.id}`} onClick={() => startEdit(c)} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"><Pencil size={13} /> Modifica</button>
                <button data-testid={`delete-${c.id}`} onClick={() => remove(c.id)} className="flex items-center gap-1.5 rounded-md border border-input bg-white px-2.5 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50"><Trash2 size={13} /> Elimina</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Connector marketplace */}
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">{t("Aggiungi un connettore")}</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {connectors.map((k) => (
          <button
            key={k.type}
            data-testid={`connector-${k.type}`}
            onClick={() => startNew(k.type)}
            className="group flex items-start gap-3 rounded-xl border border-border bg-white p-4 text-left transition-all hover:border-primary hover:-translate-y-0.5"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary"><Plus size={18} className="text-primary" /></span>
            <div>
              <p className="font-semibold">{k.name}</p>
              <p className="text-xs text-muted-foreground">{t("erp.connectorMeta", { n: k.capabilities.length, transport: k.transport.toUpperCase() })}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Sync logs */}
      <div className="mt-8">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">{t("Log di sincronizzazione")}</p>
        <div className="rounded-xl border border-border bg-white overflow-hidden">
          {jobs.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-muted-foreground">{t("Nessuna sincronizzazione ancora.")}</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-secondary/40 text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-4 py-2.5 text-left">{t("Stato")}</th><th className="px-4 py-2.5 text-left">{t("Cliente")}</th><th className="px-4 py-2.5 text-left">{t("Connettore")}</th><th className="px-4 py-2.5 text-left">{t("Tentativi")}</th><th className="px-4 py-2.5 text-left">{t("Dettaglio")}</th><th className="px-4 py-2.5"></th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {jobs.map((j) => (
                  <tr key={j.id} data-testid={`job-${j.id}`}>
                    <td className="px-4 py-2.5">
                      {j.status === "success"
                        ? <span className="flex items-center gap-1.5 text-emerald-600"><CheckCircle2 size={14} /> OK</span>
                        : <span className="flex items-center gap-1.5 text-red-500"><XCircle size={14} /> {t("Errore")}</span>}
                    </td>
                    <td className="px-4 py-2.5">{j.customer_name || "—"}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{j.connector_name}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{j.attempts}</td>
                    <td className="px-4 py-2.5 max-w-[220px] truncate text-xs text-muted-foreground" title={j.last_error || ""}>{j.last_error || t("Inviato")}</td>
                    <td className="px-4 py-2.5 text-right">
                      {j.status === "error" && (
                        <button data-testid={`retry-${j.id}`} onClick={() => retryJob(j.id)} className="flex items-center gap-1 rounded-md border border-input px-2 py-1 text-xs font-medium hover:bg-secondary"><RefreshCw size={12} /> {t("Riprova")}</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
