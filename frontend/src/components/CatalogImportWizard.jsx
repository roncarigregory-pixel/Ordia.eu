import { useState, useRef, useEffect, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  FileSpreadsheet, FileText, Image as ImageIcon, ClipboardPaste, Plus,
  Loader2, Trash2, Sparkles, Download, Save, ArrowLeft, ArrowRight,
  CheckCircle2, AlertTriangle, Copy as CopyIcon, PackageCheck,
} from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const rid = () => `r-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
const emptyRow = () => ({ _rid: rid(), name: "", sku: "", category: "General", unit: "unità", pack_size: "", price: 0, aliases: [], _uncertain: ["price"], _exists: false });
const withRids = (list) => (list || []).map((p) => ({ ...p, _rid: rid(), aliases: p.aliases || [] }));

const STEPS = ["Carica il catalogo", "Ordia capisce il catalogo", "Conferma"];

export function CatalogImportWizard({ open, onClose, onDone }) {
  const { t } = useI18n();
  const [step, setStep] = useState(1);
  const [rows, setRows] = useState([]);
  const [mode, setMode] = useState("add");
  const [busy, setBusy] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [hasDraft, setHasDraft] = useState(false);
  const fileRef = useRef(null);
  const pending = useRef(null); // which source triggered the picker

  const reset = useCallback(() => { setStep(1); setRows([]); setMode("add"); setPasteText(""); }, []);

  useEffect(() => {
    if (!open) return;
    reset();
    api.get("/catalog/import-draft").then(({ data }) => setHasDraft((data?.products || []).length > 0)).catch(() => setHasDraft(false));
  }, [open, reset]);

  const goReview = (list) => {
    if (!list.length) { toast.error(t("Nessun prodotto trovato. Prova con un file più nitido o inseriscili a mano.")); return; }
    setRows(withRids(list));
    setStep(2);
  };

  const analyzeFile = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/products/import-ai", fd, { headers: { "Content-Type": "multipart/form-data" }, timeout: 120000 });
      goReview(data.products || []);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const analyzeText = async () => {
    if (pasteText.trim().length < 3) return toast.error(t("Incolla il testo del listino."));
    setBusy(true);
    try {
      const { data } = await api.post("/products/import-ai/text", { text: pasteText });
      goReview(data.products || []);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const pickFile = (accept, src) => { pending.current = src; if (fileRef.current) { fileRef.current.accept = accept; fileRef.current.click(); } };

  const downloadTemplate = () => window.open(`${BACKEND}/api/products/template`, "_blank");

  const updateRow = (id, k, v) => setRows((prev) => prev.map((r) => r._rid === id ? { ...r, [k]: v } : r));
  const removeRow = (id) => setRows((prev) => prev.filter((r) => r._rid !== id));
  const addRow = () => setRows((prev) => [...prev, emptyRow()]);

  const saveDraft = async () => {
    try {
      await api.put("/catalog/import-draft", { products: rows.map(({ _rid, _uncertain, _exists, ...p }) => p), mode });
      toast.success(t("Bozza salvata. Puoi riprenderla più tardi."));
      setHasDraft(true);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const loadDraft = async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/catalog/import-draft");
      if (!(data?.products || []).length) return toast.info(t("Nessuna bozza salvata."));
      setRows(withRids(data.products)); setMode(data.mode || "add"); setStep(2);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const confirm = async () => {
    const valid = rows.filter((r) => r.name.trim());
    if (!valid.length) return toast.error(t("Aggiungi almeno un prodotto con il nome."));
    setBusy(true);
    try {
      const payload = valid.map(({ _rid, _uncertain, _exists, ...p }) => ({ ...p, price: parseFloat(p.price) || 0, aliases: Array.isArray(p.aliases) ? p.aliases : String(p.aliases).split(",").map((a) => a.trim()).filter(Boolean) }));
      const { data } = await api.post("/products/import-ai/confirm", { products: payload, mode });
      await api.delete("/catalog/import-draft").catch(() => {});
      toast.success(`${t("Catalogo confermato")} · +${data.inserted} ${t("nuovi")}, ↻${data.updated} ${t("aggiornati")}, ${data.skipped} ${t("saltati")}`);
      onDone?.(); onClose?.();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const dupCount = rows.filter((r) => r._exists).length;
  const newCount = rows.filter((r) => !r._exists && r.name.trim()).length;
  const uncertainCount = rows.filter((r) => (r._uncertain || []).length && r.name.trim()).length;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose?.()}>
      <DialogContent className="sm:max-w-3xl" data-testid="catalog-wizard">
        <DialogHeader>
          <DialogTitle className="font-display tracking-tight flex items-center gap-2">
            <Sparkles size={18} className="text-ai" /> {t("Importa catalogo")}
          </DialogTitle>
        </DialogHeader>

        {/* Stepper */}
        <div className="flex items-center gap-2 mb-1">
          {STEPS.map((label, i) => {
            const n = i + 1; const active = step === n; const done = step > n;
            return (
              <div key={label} className="flex items-center gap-2">
                <span data-testid={`wizard-step-${n}`} className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${done ? "bg-emerald-500 text-white" : active ? "bg-ai text-white" : "bg-slate-100 text-slate-400"}`}>{done ? "✓" : n}</span>
                <span className={`text-xs font-medium ${active ? "text-foreground" : "text-muted-foreground"} hidden sm:inline`}>{t(label)}</span>
                {n < STEPS.length && <div className="mx-1 h-px w-5 bg-slate-200" />}
              </div>
            );
          })}
        </div>

        <input ref={fileRef} type="file" className="hidden" data-testid="wizard-file-input" onChange={(e) => analyzeFile(e.target.files?.[0])} />

        {/* STEP 1 — choose source */}
        {step === 1 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{t("Non importa se il file è disordinato: ci pensa l'AI. Scegli da dove partire.")}</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <SourceCard testid="src-excel" icon={FileSpreadsheet} title={t("Excel / CSV")} onClick={() => pickFile(".csv,.xlsx,.xls", "excel")} />
              <SourceCard testid="src-pdf" icon={FileText} title={t("PDF")} onClick={() => pickFile(".pdf", "pdf")} />
              <SourceCard testid="src-photo" icon={ImageIcon} title={t("Foto / Screenshot")} onClick={() => pickFile(".png,.jpg,.jpeg,.webp,.heic,.heif", "photo")} />
              <SourceCard testid="src-paste" icon={ClipboardPaste} title={t("Incolla testo")} onClick={() => setStep(1.5)} />
              <SourceCard testid="src-manual" icon={Plus} title={t("Inserisci a mano")} onClick={() => { setRows([emptyRow()]); setStep(2); }} />
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button data-testid="wizard-download-template" onClick={downloadTemplate} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary">
                <Download size={15} /> {t("Scarica il modello Excel")}
              </button>
              {hasDraft && (
                <button data-testid="wizard-load-draft" onClick={loadDraft} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary">
                  <Save size={15} /> {t("Riprendi bozza")}
                </button>
              )}
            </div>
            <div className="rounded-lg bg-secondary/60 p-3 text-xs text-muted-foreground">
              <b>{t("Esempi che funzionano")}:</b> {t("un Excel con colonne nome/prezzo, un PDF del listino del fornitore, la foto di un listino cartaceo, oppure righe copiate come")} <span className="font-mono">Mozzarella 400g 6,50</span>.
            </div>
            {busy && <div className="flex items-center gap-2 text-sm text-ai"><Loader2 size={16} className="animate-spin" /> {t("L'AI sta leggendo il catalogo…")}</div>}
          </div>
        )}

        {/* STEP 1.5 — paste text */}
        {step === 1.5 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{t("Incolla qui il listino, anche disordinato. Una riga per prodotto se possibile.")}</p>
            <textarea data-testid="wizard-paste-text" value={pasteText} onChange={(e) => setPasteText(e.target.value)} rows={8}
              placeholder={"Mozzarella fiordilatte 400g - 6,50 €\nPassata di pomodoro cassa 12x700g 9,90\n..."}
              className="w-full rounded-lg border border-input bg-white p-3 text-sm font-mono outline-none focus:ring-2 focus:ring-ring" />
            <div className="flex items-center justify-between">
              <button data-testid="wizard-paste-back" onClick={() => setStep(1)} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary"><ArrowLeft size={15} /> {t("Indietro")}</button>
              <button data-testid="wizard-paste-analyze" disabled={busy} onClick={analyzeText} className="inline-flex items-center gap-1.5 rounded-lg bg-ai text-white px-4 py-2 text-sm font-semibold hover:bg-ai/90 disabled:opacity-60">
                {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {t("Leggi con l'AI")}
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 — review editable table */}
        {step === 2 && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1 text-muted-foreground"><PackageCheck size={14} /> {rows.length} {t("prodotti")}</span>
              {dupCount > 0 && <span data-testid="wizard-dup-count" className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-amber-600"><CopyIcon size={12} /> {dupCount} {t("già in catalogo")}</span>}
              {uncertainCount > 0 && <span data-testid="wizard-uncertain-count" className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2 py-0.5 text-orange-600"><AlertTriangle size={12} /> {uncertainCount} {t("da controllare")}</span>}
            </div>
            <p className="text-sm text-muted-foreground -mt-1">{t("Correggi solo ciò che serve. I campi arancioni sono quelli su cui l'AI è meno sicura.")}</p>

            <div className="max-h-[46vh] overflow-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-secondary">
                  <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="px-2 py-2">{t("Nome")}</th>
                    <th className="px-2 py-2 w-24">SKU</th>
                    <th className="px-2 py-2 w-20">{t("Unità")}</th>
                    <th className="px-2 py-2 w-24 text-right">{t("Prezzo")}</th>
                    <th className="px-2 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rows.map((r) => {
                    const unc = r._uncertain || [];
                    return (
                      <tr key={r._rid} data-testid={`wizard-row-${r._rid}`} className={r._exists ? "bg-amber-50/40" : ""}>
                        <td className="px-2 py-1.5">
                          <input value={r.name} onChange={(e) => updateRow(r._rid, "name", e.target.value)} placeholder={t("Nome prodotto")} className="w-full rounded-md border border-input bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring" />
                          {r._exists && <span className="text-[10px] text-amber-600">{t("già presente — verrà aggiornato o saltato")}</span>}
                        </td>
                        <td className="px-2 py-1.5"><input value={r.sku || ""} onChange={(e) => updateRow(r._rid, "sku", e.target.value)} className={`w-full rounded-md border bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring ${unc.includes("sku") ? "border-orange-300" : "border-input"}`} /></td>
                        <td className="px-2 py-1.5"><input value={r.unit || ""} onChange={(e) => updateRow(r._rid, "unit", e.target.value)} className="w-full rounded-md border border-input bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring" /></td>
                        <td className="px-2 py-1.5"><input type="number" step="0.01" value={r.price} onChange={(e) => updateRow(r._rid, "price", parseFloat(e.target.value) || 0)} className={`w-full rounded-md border bg-white px-2 py-1.5 text-right font-mono text-sm outline-none focus:ring-2 focus:ring-ring ${unc.includes("price") ? "border-orange-300 bg-orange-50/50" : "border-input"}`} /></td>
                        <td className="px-2 py-1.5 text-right"><button data-testid={`wizard-remove-${r._rid}`} onClick={() => removeRow(r._rid)} className="text-slate-300 hover:text-red-500 p-1"><Trash2 size={15} /></button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <button data-testid="wizard-add-row" onClick={addRow} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary"><Plus size={15} /> {t("Aggiungi riga")}</button>
              <div className="flex items-center gap-2">
                <button data-testid="wizard-save-draft" onClick={saveDraft} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary"><Save size={15} /> {t("Salva bozza")}</button>
                <button data-testid="wizard-to-confirm" onClick={() => setStep(3)} className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold hover:bg-primary/90"><ArrowRight size={15} /> {t("Continua")}</button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3 — confirm */}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{t("Quasi fatto. Scegli come salvare il catalogo.")}</p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <Stat n={newCount} label={t("nuovi")} />
              <Stat n={dupCount} label={t("già presenti")} />
              <Stat n={uncertainCount} label={t("da controllare")} />
            </div>
            <div className="space-y-2">
              <ModeOption testid="mode-add" active={mode === "add"} onClick={() => setMode("add")} title={t("Aggiungi solo i nuovi")} desc={t("I prodotti già presenti vengono lasciati come sono (nessun duplicato).")} />
              <ModeOption testid="mode-update" active={mode === "update"} onClick={() => setMode("update")} title={t("Aggiorna il catalogo esistente")} desc={t("Aggiorna prezzo e dati dei prodotti già presenti (abbinati per SKU o nome) e aggiunge i nuovi.")} />
            </div>
            <div className="flex items-center justify-between">
              <button data-testid="wizard-back-to-review" onClick={() => setStep(2)} className="inline-flex items-center gap-1.5 rounded-lg border border-input bg-white px-3 py-2 text-sm font-medium hover:bg-secondary"><ArrowLeft size={15} /> {t("Indietro")}</button>
              <button data-testid="wizard-confirm" disabled={busy} onClick={confirm} className="inline-flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold hover:bg-primary/90 disabled:opacity-60">
                {busy ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />} {t("Conferma catalogo")}
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function SourceCard({ icon: Icon, title, onClick, testid }) {
  return (
    <button data-testid={testid} onClick={onClick} className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border bg-white p-4 hover:border-ai hover:bg-ai/5 transition-colors">
      <Icon size={22} className="text-ai" />
      <span className="text-xs font-medium text-center">{title}</span>
    </button>
  );
}

function Stat({ n, label }) {
  return (
    <div className="rounded-lg bg-secondary p-3">
      <div className="font-display text-2xl font-black text-foreground">{n}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function ModeOption({ active, onClick, title, desc, testid }) {
  return (
    <button data-testid={testid} onClick={onClick} className={`w-full text-left rounded-xl border p-3 transition-colors ${active ? "border-ai bg-ai/5 ring-1 ring-ai" : "border-border bg-white hover:bg-secondary"}`}>
      <div className="flex items-center gap-2">
        <span className={`h-4 w-4 rounded-full border-2 ${active ? "border-ai bg-ai" : "border-slate-300"}`} />
        <span className="text-sm font-semibold">{title}</span>
      </div>
      <p className="mt-1 pl-6 text-xs text-muted-foreground">{desc}</p>
    </button>
  );
}
