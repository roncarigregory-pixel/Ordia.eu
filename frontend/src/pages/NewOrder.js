import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { TextT, UploadSimple, FileArrowUp, Sparkle, ArrowRight } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

const SAMPLE = `Ciao, sono Maria della Trattoria Sole. Per consegna giovedì:
- 3 casse mozzarella
- 2 sacchi farina 00
- 5 scatole pomodori pelati
- 10kg petto di pollo
- una cassa di coca
Grazie!`;

const STAGES = ["Lettura sorgente", "Comprensione", "Abbinamento catalogo", "Validazione"];

export default function NewOrder() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const fileInput = useRef(null);

  const runStages = () => {
    setStage(0);
    let i = 0;
    const t = setInterval(() => {
      i += 1;
      if (i < STAGES.length) setStage(i);
      else clearInterval(t);
    }, 900);
    return t;
  };

  const submit = async () => {
    if (tab === "text" && !text.trim()) return toast.error("Incolla prima un ordine.");
    if (tab === "file" && !file) return toast.error("Scegli prima un file.");
    setLoading(true);
    const timer = runStages();
    try {
      const fd = new FormData();
      fd.append("source_type", tab);
      if (tab === "text") fd.append("text", text);
      else fd.append("file", file);
      const { data } = await api.post("/orders/extract", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Ordine estratto");
      navigate(`/app/orders/${data.id}`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      setTab("file");
    }
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto py-16 animate-fade-up">
        <div className="flex items-center gap-2 mb-8">
          <Sparkle size={22} weight="fill" className="text-slate-900" />
          <h1 className="font-display text-2xl font-black tracking-tight">Voxera sta leggendo il tuo ordine…</h1>
        </div>
        <div className="space-y-3">
          {STAGES.map((s, i) => (
            <div
              key={s}
              data-testid={`extract-stage-${i}`}
              className={cn(
                "flex items-center gap-3 rounded-md border px-4 py-3 transition-colors",
                i < stage ? "border-emerald-200 bg-emerald-50" : i === stage ? "border-slate-300 bg-white" : "border-border bg-white opacity-50"
              )}
            >
              <div className={cn("h-2 w-2 rounded-full", i < stage ? "bg-emerald-500" : i === stage ? "bg-slate-900 animate-pulse" : "bg-slate-300")} />
              <span className="text-sm font-medium">{s}</span>
              {i < stage && <span className="ml-auto text-xs text-emerald-600 font-medium">Fatto</span>}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto animate-fade-up">
      <h1 className="font-display text-4xl font-black tracking-tighter">Nuovo Ordine</h1>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Incolla un messaggio o trascina un file — testo WhatsApp, email, PDF, Excel, CSV, una foto o un messaggio vocale.
      </p>

      <div className="inline-flex rounded-md border border-border bg-white p-1 mb-4">
        <button
          data-testid="tab-text"
          onClick={() => setTab("text")}
          className={cn("flex items-center gap-2 rounded px-4 py-1.5 text-sm font-medium transition-colors", tab === "text" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
        >
          <TextT size={16} /> Incolla testo
        </button>
        <button
          data-testid="tab-file"
          onClick={() => setTab("file")}
          className={cn("flex items-center gap-2 rounded px-4 py-1.5 text-sm font-medium transition-colors", tab === "file" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
        >
          <UploadSimple size={16} /> Carica file
        </button>
      </div>

      {tab === "text" ? (
        <div>
          <textarea
            data-testid="order-text-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={12}
            placeholder="Incolla qui il messaggio d'ordine in arrivo…"
            className="w-full rounded-md border border-input bg-white p-4 text-sm font-mono leading-relaxed outline-none focus:ring-2 focus:ring-ring resize-none"
          />
          <button
            data-testid="use-sample-order"
            onClick={() => setText(SAMPLE)}
            className="mt-2 text-xs text-muted-foreground hover:text-foreground underline underline-offset-4"
          >
            Usa un ordine di esempio
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileInput.current?.click()}
          data-testid="file-dropzone"
          className={cn(
            "cursor-pointer rounded-md border-2 border-dashed px-6 py-16 text-center transition-colors",
            dragging ? "border-slate-900 bg-secondary" : "border-border bg-white hover:border-slate-300"
          )}
        >
          <FileArrowUp size={36} className="mx-auto text-slate-400" />
          <p className="mt-3 text-sm font-medium">{file ? file.name : "Trascina un file o clicca per sfogliare"}</p>
          <p className="mt-1 text-xs text-muted-foreground">PDF · Excel · CSV · PNG · JPG · WEBP · Vocale (MP3, M4A, WAV, OGG)</p>
          <input
            ref={fileInput}
            type="file"
            data-testid="file-input"
            accept=".pdf,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.mp3,.mp4,.m4a,.wav,.webm,.ogg,.mpeg,.mpga,audio/*"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
      )}

      <button
        data-testid="extract-order-button"
        onClick={submit}
        className="mt-5 w-full flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-3 text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        <Sparkle size={18} weight="fill" /> Estrai ordine
        <ArrowRight size={16} weight="bold" />
      </button>
    </div>
  );
}
