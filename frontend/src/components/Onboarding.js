import { createContext, useContext, useState, useEffect, useCallback, useLayoutEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Play, HelpCircle, X, ArrowRight, ArrowLeft, Sparkles, MessageSquare,
  ScanText, CheckCircle2, Send, BookOpen, Compass, Film,
} from "lucide-react";

/* ------------------------------------------------------------------ *
 * OFFICIAL TUTORIAL VIDEO — swap this single object to go live.
 * type: "" (placeholder) | "mp4" | "youtube"
 * src : full mp4 URL, or the YouTube video ID (e.g. "dQw4w9WgXcQ")
 * The same asset is reusable for site / landing / social / demos.
 * ------------------------------------------------------------------ */
export const ORDIA_TUTORIAL_VIDEO = {
  type: "", // "" while we wait for the final cut → shows the branded placeholder
  src: "",
  poster: "https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/a948ca6385b0a67de5e0c7210fd6dcf546b499f2df671ced7bbdf3cced50119f.png",
};

const WELCOME_KEY = "ordia.onboarding.welcome.v1";

const HOW_IT_WORKS = [
  { icon: MessageSquare, title: "Arriva un ordine", body: "Da WhatsApp, email, PDF, Excel, foto o altri canali." },
  { icon: ScanText, title: "Ordia lo legge", body: "L'AI estrae cliente, articoli e quantità automaticamente." },
  { icon: CheckCircle2, title: "Controlli le incertezze", body: "Solo le righe dubbie sono evidenziate. Il resto è pronto." },
  { icon: Send, title: "Approvi e va nel gestionale", body: "Un click: l'ordine è inviato o preparato per il tuo ERP." },
];

const TOUR_STEPS = [
  { selector: "new-order-cta", title: "Inizia da qui", body: "Incolla o carica un ordine (WhatsApp, email, PDF, Excel, foto). Ordia lo legge con l'AI in pochi secondi." },
  { selector: "nav-orders", title: "I tuoi ordini", body: "Qui trovi gli ordini letti dall'AI. Le righe incerte sono evidenziate: controlli e clicchi Approva." },
  { selector: "nav-notifications", title: "Avvisi intelligenti", body: "Ordia ti segnala solo ciò che richiede attenzione. Niente rumore." },
  { selector: "nav-setup", title: "Collega i tuoi canali", body: "Email, WhatsApp e il gestionale. Si configura una volta sola." },
  { selector: "onboarding-help-btn", title: "Aiuto sempre a portata", body: "Rivedi il video o questo tour quando vuoi, da qui." },
];

const FAQS = [
  { q: "Come arrivano gli ordini in Ordia?", a: "Automaticamente dai canali collegati (WhatsApp, email), oppure incollandoli o caricandoli con il pulsante \"Nuovo Ordine\"." },
  { q: "Devo controllare ogni ordine riga per riga?", a: "No. Ordia evidenzia solo le righe \"incerte\". Il resto è già compilato e verificato: ti basta un'occhiata e Approva." },
  { q: "Funziona con il mio gestionale?", a: "Sì. Tramite API, file o il Bridge di Ordia — che inserisce gli ordini anche in gestionali senza API." },
  { q: "I miei dati sono al sicuro?", a: "Sì. Sei tu a confermare prima dell'invio: nessun inserimento automatico cieco. Le credenziali del gestionale restano tue." },
  { q: "Come inserisco un ordine manualmente?", a: "Con il pulsante \"Nuovo Ordine\" in alto a sinistra: incolli il testo o carichi un file e l'AI fa il resto." },
];

const OnboardingContext = createContext(null);
export const useOnboarding = () => useContext(OnboardingContext);

/* ---------------------------- Video player ---------------------------- */
function VideoPlayer() {
  const v = ORDIA_TUTORIAL_VIDEO;
  if (v.type === "youtube" && v.src)
    return (
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe title="Ordia tutorial" className="h-full w-full"
          src={`https://www.youtube.com/embed/${v.src}?rel=0`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen />
      </div>
    );
  if (v.type === "mp4" && v.src)
    return (
      <video className="aspect-video w-full rounded-xl bg-black" controls poster={v.poster} data-testid="tutorial-video">
        <source src={v.src} type="video/mp4" />
      </video>
    );
  // Placeholder until the final video is provided
  return (
    <div data-testid="video-placeholder"
      className="relative aspect-video w-full overflow-hidden rounded-xl border border-border"
      style={{ backgroundImage: `url(${v.poster})`, backgroundSize: "cover", backgroundPosition: "center" }}>
      <div className="absolute inset-0 bg-black/25" />
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/90 shadow-lg">
          <Play size={26} className="ml-1 text-primary" fill="currentColor" />
        </div>
        <span className="rounded-full bg-black/50 px-3 py-1 text-xs font-medium text-white">Video tutorial in arrivo · 90s</span>
      </div>
    </div>
  );
}

/* ---------------------------- Spotlight tour ---------------------------- */
function GuidedTour({ step, total, onNext, onPrev, onClose }) {
  const [rect, setRect] = useState(null);
  const cfg = TOUR_STEPS[step];

  useLayoutEffect(() => {
    const measure = () => {
      const el = document.querySelector(`[data-testid="${cfg.selector}"]`);
      if (!el) { setRect(null); return; }
      el.scrollIntoView({ block: "nearest" });
      setRect(el.getBoundingClientRect());
    };
    measure();
    window.addEventListener("resize", measure);
    const t = setTimeout(measure, 60);
    return () => { window.removeEventListener("resize", measure); clearTimeout(t); };
  }, [cfg.selector]);

  // Tooltip placement: to the right of the highlighted element, clamped to viewport.
  const tipStyle = rect
    ? { top: Math.min(Math.max(rect.top, 16), window.innerHeight - 220), left: Math.min(rect.right + 16, window.innerWidth - 340) }
    : { top: window.innerHeight / 2 - 100, left: window.innerWidth / 2 - 170 };

  return createPortal(
    <div className="fixed inset-0 z-[100]" data-testid="guided-tour">
      {/* dimmed backdrop with spotlight cutout via huge box-shadow */}
      <div className="absolute inset-0" onClick={onClose} />
      {rect && (
        <div className="pointer-events-none absolute rounded-xl transition-all duration-300"
          style={{
            top: rect.top - 6, left: rect.left - 6, width: rect.width + 12, height: rect.height + 12,
            boxShadow: "0 0 0 9999px rgba(11,30,59,0.72)", outline: "2px solid rgba(16,185,129,0.9)", borderRadius: 12,
          }} />
      )}
      <div className="absolute w-[320px] rounded-2xl border border-border bg-white p-5 shadow-2xl transition-all duration-200"
        style={tipStyle} data-testid="tour-tooltip">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
          <Sparkles size={13} /> Passo {step + 1} di {total}
        </div>
        <h3 className="mt-2 font-display text-lg font-bold tracking-tight text-foreground">{cfg.title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{cfg.body}</p>
        <div className="mt-4 flex items-center justify-between">
          <div className="flex gap-1">
            {TOUR_STEPS.map((_, i) => (
              <span key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-5 bg-primary" : "w-1.5 bg-slate-200"}`} />
            ))}
          </div>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <button data-testid="tour-prev" onClick={onPrev} className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary">
                <ArrowLeft size={16} />
              </button>
            )}
            <button data-testid="tour-next" onClick={onNext}
              className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
              {step === total - 1 ? "Fine" : "Avanti"} <ArrowRight size={15} />
            </button>
          </div>
        </div>
        <button data-testid="tour-skip" onClick={onClose} className="absolute -top-2 -right-2 rounded-full bg-white p-1 shadow border border-border text-muted-foreground hover:text-foreground">
          <X size={14} />
        </button>
      </div>
    </div>,
    document.body
  );
}

/* ---------------------------- Provider ---------------------------- */
export function OnboardingProvider({ children }) {
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [videoOpen, setVideoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourStep, setTourStep] = useState(null); // null = off

  useEffect(() => {
    if (!localStorage.getItem(WELCOME_KEY)) {
      const t = setTimeout(() => setWelcomeOpen(true), 600);
      return () => clearTimeout(t);
    }
  }, []);

  const markWelcomeSeen = () => localStorage.setItem(WELCOME_KEY, "1");
  const closeWelcome = () => { markWelcomeSeen(); setWelcomeOpen(false); };
  const startTour = useCallback(() => { setWelcomeOpen(false); setHelpOpen(false); markWelcomeSeen(); setTourStep(0); }, []);
  const openVideo = useCallback(() => { setWelcomeOpen(false); markWelcomeSeen(); setVideoOpen(true); }, []);
  const openHelp = useCallback(() => setHelpOpen(true), []);

  const value = useMemo(() => ({ startTour, openVideo, openHelp, openWelcome: () => setWelcomeOpen(true) }),
    [startTour, openVideo, openHelp]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}

      {/* Floating help launcher — always available */}
      <button data-testid="onboarding-help-btn" onClick={openHelp} title="Guida & tour"
        className="fixed bottom-20 md:bottom-6 right-5 z-[70] flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-xl transition-transform hover:scale-105">
        <HelpCircle size={22} />
      </button>

      {/* Welcome modal (first login) */}
      <Dialog open={welcomeOpen} onOpenChange={(o) => { if (!o) closeWelcome(); }}>
        <DialogContent className="max-w-lg" data-testid="onboarding-welcome">
          <DialogHeader>
            <DialogTitle className="font-display text-2xl tracking-tight">Benvenuto in Ordia 👋</DialogTitle>
            <DialogDescription className="text-base">Dagli ordini caotici agli ordini pronti — in automatico. Ecco come funziona:</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3 py-2">
            {HOW_IT_WORKS.map((s, i) => (
              <div key={i} className="rounded-xl border border-border bg-secondary/40 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary"><s.icon size={17} /></div>
                <p className="mt-2 text-sm font-semibold text-foreground">{s.title}</p>
                <p className="text-xs text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-2">
            <button data-testid="welcome-watch-video" onClick={openVideo}
              className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
              <Play size={16} fill="currentColor" /> Guarda il video (90s)
            </button>
            <div className="flex gap-2">
              <button data-testid="welcome-start-tour" onClick={startTour}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-semibold hover:bg-secondary">
                <Compass size={16} /> Fai il tour guidato
              </button>
              <button data-testid="welcome-skip" onClick={closeWelcome}
                className="rounded-lg px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-secondary">
                Inizia subito
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Video modal */}
      <Dialog open={videoOpen} onOpenChange={setVideoOpen}>
        <DialogContent className="max-w-2xl" data-testid="onboarding-video-modal">
          <DialogHeader>
            <DialogTitle className="font-display text-xl tracking-tight flex items-center gap-2"><Film size={18} /> Come funziona Ordia</DialogTitle>
            <DialogDescription>Il flusso completo in 90 secondi: dall'ordine ricevuto all'ordine nel gestionale.</DialogDescription>
          </DialogHeader>
          <VideoPlayer />
        </DialogContent>
      </Dialog>

      {/* Help / Guida panel */}
      <Sheet open={helpOpen} onOpenChange={setHelpOpen}>
        <SheetContent className="w-full sm:max-w-md overflow-y-auto" data-testid="onboarding-help-panel">
          <SheetHeader>
            <SheetTitle className="font-display text-xl tracking-tight flex items-center gap-2"><BookOpen size={18} /> Guida</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-2">
            <button data-testid="help-watch-video" onClick={() => { setHelpOpen(false); openVideo(); }}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-secondary/40 p-3 text-left hover:bg-secondary">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground"><Play size={16} fill="currentColor" /></div>
              <div><p className="text-sm font-semibold">Guarda il video tutorial</p><p className="text-xs text-muted-foreground">Il flusso completo in 90 secondi</p></div>
            </button>
            <button data-testid="help-replay-tour" onClick={startTour}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-secondary/40 p-3 text-left hover:bg-secondary">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Compass size={16} /></div>
              <div><p className="text-sm font-semibold">Rivedi il tour guidato</p><p className="text-xs text-muted-foreground">Un giro veloce dell'interfaccia</p></div>
            </button>
          </div>
          <div className="mt-6">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Domande frequenti</p>
            <Accordion type="single" collapsible className="w-full">
              {FAQS.map((f, i) => (
                <AccordionItem key={i} value={`faq-${i}`} data-testid={`faq-${i}`}>
                  <AccordionTrigger className="text-left text-sm">{f.q}</AccordionTrigger>
                  <AccordionContent className="text-sm text-muted-foreground">{f.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </SheetContent>
      </Sheet>

      {/* Interactive tour */}
      {tourStep !== null && (
        <GuidedTour
          step={tourStep} total={TOUR_STEPS.length}
          onNext={() => setTourStep((s) => (s + 1 >= TOUR_STEPS.length ? null : s + 1))}
          onPrev={() => setTourStep((s) => Math.max(0, s - 1))}
          onClose={() => setTourStep(null)}
        />
      )}
    </OnboardingContext.Provider>
  );
}
