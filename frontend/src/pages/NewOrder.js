import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import {
  Type, MessageCircle, Mail, FileText, FileSpreadsheet, Sheet,
  Image as ImageIcon, Mic, UploadCloud, Sparkles, ArrowRight, Check, Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const SAMPLE = `Ciao, sono Maria della Trattoria Sole. Per consegna giovedì:
- 3 casse mozzarella
- 2 sacchi farina 00
- 5 scatole pomodori pelati
- 10kg petto di pollo
- una cassa di coca
Grazie!`;

const CHANNELS = [
  { id: "text", label: "Testo", desc: "Scrivi o incolla", icon: Type, mode: "text" },
  { id: "whatsapp", label: "WhatsApp", desc: "Incolla la chat", icon: MessageCircle, mode: "text" },
  { id: "email", label: "Email", desc: "Incolla il messaggio", icon: Mail, mode: "text" },
  { id: "pdf", label: "PDF", desc: "Documento ordine", icon: FileText, mode: "file", accept: ".pdf" },
  { id: "excel", label: "Excel", desc: ".xlsx / .xls", icon: Sheet, mode: "file", accept: ".xlsx,.xls" },
  { id: "csv", label: "CSV", desc: "Tabella dati", icon: FileSpreadsheet, mode: "file", accept: ".csv" },
  { id: "image", label: "Foto", desc: "Immagine ordine", icon: ImageIcon, mode: "file", accept: ".png,.jpg,.jpeg,.webp" },
  { id: "audio", label: "Vocale", desc: "Messaggio audio", icon: Mic, mode: "file", accept: ".mp3,.m4a,.wav,.ogg,.webm,audio/*" },
];

const PLACEHOLDER = {
  text: "Incolla o scrivi qui il messaggio d'ordine…",
  whatsapp: "Incolla qui la conversazione WhatsApp del cliente…",
  email: "Incolla qui il testo dell'email d'ordine…",
};

const STAGES = [
  "Caricamento sorgente",
  "Estrazione AI",
  "Riconoscimento cliente",
  "Abbinamento catalogo",
  "Calcolo confidenza",
  "Ordine pronto",
];

export default function NewOrder() {
  const navigate = useNavigate();
  const [channel, setChannel] = useState(CHANNELS[0]);
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
      if (i < STAGES.length - 1) setStage(i);
      else clearInterval(t);
    }, 850);
    return t;
  };

  const submit = async () => {
    const isText = channel.mode === "text";
    if (isText && !text.trim()) return toast.error("Scrivi o incolla prima un ordine.");
    if (!isText && !file) return toast.error("Scegli prima un file.");
    setLoading(true);
    const timer = runStages();
    try {
      const fd = new FormData();
      fd.append("source_type", isText ? "text" : "file");
      if (isText) fd.append("text", text);
      else fd.append("file", file);
      const { data } = await api.post("/orders/extract", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      clearInterval(timer);
      setStage(STAGES.length - 1);
      await new Promise((r) => setTimeout(r, 550));
      toast.success("Ordine estratto");
      navigate(`/app/orders/${data.id}`);
    } catch (err) {
      clearInterval(timer);
      setLoading(false);
      toast.error(formatApiError(err));
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    setFile(f);
    const name = f.name.toLowerCase();
    const match = CHANNELS.find((c) => c.accept && c.accept.split(",").some((ext) => ext.startsWith(".") && name.endsWith(ext.trim())))
      || CHANNELS.find((c) => c.id === (f.type.startsWith("image") ? "image" : f.type.startsWith("audio") ? "audio" : "pdf"));
    if (match) setChannel(match);
  };

  const pickChannel = (c) => {
    setChannel(c);
    setFile(null);
    if (c.mode === "file") setTimeout(() => fileInput.current?.click(), 50);
  };

  if (loading) {
    return (
      <div className="max-w-lg mx-auto py-16">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-10">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ai-soft">
            <Sparkles size={20} className="text-ai" />
          </span>
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight">Ordia sta leggendo l'ordine</h1>
            <p className="text-sm text-muted-foreground">Estrazione intelligente in corso…</p>
          </div>
        </motion.div>
        <div className="space-y-2.5">
          {STAGES.map((s, i) => {
            const done = i < stage;
            const active = i === stage;
            return (
              <motion.div
                key={s}
                data-testid={`extract-stage-${i}`}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: done || active ? 1 : 0.45, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                  done ? "border-emerald-200 bg-emerald-50" : active ? "border-ai/40 bg-ai-soft" : "border-border bg-white"
                )}
              >
                <span className="flex h-6 w-6 items-center justify-center">
                  {done ? <Check size={16} className="text-emerald-600" />
                    : active ? <Loader2 size={16} className="text-ai animate-spin" />
                      : <span className="h-2 w-2 rounded-full bg-slate-300" />}
                </span>
                <span className={cn("text-sm font-medium", done ? "text-emerald-700" : active ? "text-ai" : "text-muted-foreground")}>{s}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto animate-fade-up">
      <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight">Nuovo Ordine</h1>
      <p className="mt-2 text-sm text-muted-foreground mb-8">
        Scegli un canale o trascina un file. Ordia estrae automaticamente cliente, articoli e quantità.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {CHANNELS.map((c) => {
          const active = channel.id === c.id;
          return (
            <button
              key={c.id}
              data-testid={`channel-${c.id}`}
              onClick={() => pickChannel(c)}
              className={cn(
                "group flex flex-col items-start gap-3 rounded-xl border p-4 text-left transition-all",
                active ? "border-primary bg-primary text-primary-foreground shadow-sm"
                  : "border-border bg-white hover:border-slate-300 hover:-translate-y-0.5"
              )}
            >
              <c.icon size={22} className={active ? "text-primary-foreground" : "text-primary"} />
              <div>
                <p className="text-sm font-semibold">{c.label}</p>
                <p className={cn("text-xs", active ? "text-primary-foreground/70" : "text-muted-foreground")}>{c.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {channel.mode === "text" ? (
          <motion.div key="text" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <textarea
              data-testid="order-text-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={11}
              placeholder={PLACEHOLDER[channel.id]}
              className="w-full rounded-xl border border-input bg-white p-4 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring resize-none"
            />
            <button
              data-testid="use-sample-order"
              onClick={() => setText(SAMPLE)}
              className="mt-2 text-xs text-muted-foreground hover:text-foreground underline underline-offset-4"
            >
              Usa un ordine di esempio
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="file"
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileInput.current?.click()}
            data-testid="file-dropzone"
            className={cn(
              "cursor-pointer rounded-xl border-2 border-dashed px-6 py-16 text-center transition-colors",
              dragging ? "border-primary bg-ai-soft" : "border-border bg-white hover:border-slate-300"
            )}
          >
            <UploadCloud size={40} className="mx-auto text-slate-400" />
            <p className="mt-4 text-sm font-medium">{file ? file.name : `Trascina un file ${channel.label} o clicca per sfogliare`}</p>
            <p className="mt-1 text-xs text-muted-foreground">PDF · Excel · CSV · Immagini · Vocali</p>
            <input
              ref={fileInput}
              type="file"
              data-testid="file-input"
              accept={channel.accept || ".pdf,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.mp3,.m4a,.wav,.ogg,.webm,audio/*"}
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <button
        data-testid="extract-order-button"
        onClick={submit}
        className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl bg-primary text-primary-foreground px-4 py-3.5 text-sm font-semibold hover:bg-primary/90 transition-colors"
      >
        <Sparkles size={18} /> Estrai ordine con l'AI
        <ArrowRight size={16} />
      </button>
    </div>
  );
}
