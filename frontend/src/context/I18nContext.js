import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";

const STORAGE_KEY = "ordia.lang";

const DICT = {
  it: {
    "nav.login": "Accedi",
    "nav.demo": "Prova la demo",
    "nav.product": "Prodotto",
    "nav.how": "Come funziona",
    "nav.benefits": "Vantaggi",

    "hero.badge": "Automazione ordini con AI",
    "hero.title": "Basta ridigitare gli ordini a mano.",
    "hero.sub": "Ordia trasforma ogni ordine — WhatsApp, email, PDF, foto — in un ordine pronto per il tuo gestionale. In automatico.",
    "hero.cta": "Prova la demo live",
    "hero.cta.loading": "Apertura demo…",
    "hero.watch": "Guarda il video (90s)",
    "hero.trust": "Nessuna carta di credito · Demo pronta in 3 secondi",
    "hero.stat1": "ore risparmiate a settimana",
    "hero.stat2": "meno errori di digitazione",
    "hero.stat3": "canali gestiti da un solo posto",

    "how.kicker": "Come funziona",
    "how.title": "Dall'ordine caotico all'ordine pronto, in 3 passaggi",
    "how.s1.t": "Ricevi l'ordine",
    "how.s1.d": "Il cliente scrive come vuole: WhatsApp, email, un PDF o persino una foto.",
    "how.s2.t": "L'AI lo legge",
    "how.s2.d": "Ordia riconosce cliente, prodotti e quantità e li abbina al tuo catalogo.",
    "how.s3.t": "Pronto per il gestionale",
    "how.s3.d": "Controlli solo le righe incerte, approvi, e l'ordine è pronto da esportare.",

    "ben.kicker": "Perché Ordia",
    "ben.title": "Meno lavoro manuale. Più tempo per vendere.",
    "ben.1.t": "Risparmi ore ogni giorno",
    "ben.1.d": "Niente più copia-incolla: gli ordini si compilano da soli.",
    "ben.2.t": "Meno errori, meno resi",
    "ben.2.d": "Prodotti e quantità abbinati con precisione al tuo listino.",
    "ben.3.t": "Tutti i canali, un solo posto",
    "ben.3.d": "WhatsApp, email, PDF, Excel, foto e voce: tutto in un'unica coda.",
    "ben.4.t": "Si collega al tuo gestionale",
    "ben.4.d": "Esporti l'ordine pronto o lo invii direttamente al tuo ERP.",

    "chan.title": "Accetta ordini da qualsiasi canale",
    "chan.wa": "WhatsApp", "chan.email": "Email", "chan.pdf": "PDF",
    "chan.xls": "Excel", "chan.photo": "Foto", "chan.voice": "Voce",

    "cta.title": "Pronto a dire addio alla digitazione manuale?",
    "cta.sub": "Prova Ordia con dati reali di un ingrosso alimentare. Bastano pochi secondi.",
    "cta.button": "Prova la demo live",

    "foot.tag": "Dagli ordini caotici agli ordini pronti.",
    "video.title": "Ordia in 90 secondi",
  },
  en: {
    "nav.login": "Log in",
    "nav.demo": "Try the demo",
    "nav.product": "Product",
    "nav.how": "How it works",
    "nav.benefits": "Benefits",

    "hero.badge": "AI order automation",
    "hero.title": "Stop retyping orders by hand.",
    "hero.sub": "Ordia turns every order — WhatsApp, email, PDF, photo — into a clean order ready for your ERP. Automatically.",
    "hero.cta": "Try the live demo",
    "hero.cta.loading": "Opening demo…",
    "hero.watch": "Watch the video (90s)",
    "hero.trust": "No credit card · Live demo in 3 seconds",
    "hero.stat1": "hours saved per week",
    "hero.stat2": "fewer typing errors",
    "hero.stat3": "channels handled in one place",

    "how.kicker": "How it works",
    "how.title": "From messy message to order-ready, in 3 steps",
    "how.s1.t": "Receive the order",
    "how.s1.d": "Customers write however they like: WhatsApp, email, a PDF or even a photo.",
    "how.s2.t": "AI reads it",
    "how.s2.d": "Ordia recognizes the customer, products and quantities and matches them to your catalog.",
    "how.s3.t": "Ready for your ERP",
    "how.s3.d": "You only review the uncertain lines, approve, and the order is ready to export.",

    "ben.kicker": "Why Ordia",
    "ben.title": "Less manual work. More time to sell.",
    "ben.1.t": "Save hours every day",
    "ben.1.d": "No more copy-paste: orders fill themselves in.",
    "ben.2.t": "Fewer errors, fewer returns",
    "ben.2.d": "Products and quantities matched precisely to your price list.",
    "ben.3.t": "Every channel, one inbox",
    "ben.3.d": "WhatsApp, email, PDF, Excel, photos and voice — all in a single queue.",
    "ben.4.t": "Connects to your ERP",
    "ben.4.d": "Export the finished order or push it straight into your management system.",

    "chan.title": "Accept orders from any channel",
    "chan.wa": "WhatsApp", "chan.email": "Email", "chan.pdf": "PDF",
    "chan.xls": "Excel", "chan.photo": "Photo", "chan.voice": "Voice",

    "cta.title": "Ready to say goodbye to manual data entry?",
    "cta.sub": "Try Ordia with real data from a food wholesaler. It only takes seconds.",
    "cta.button": "Try the live demo",

    "foot.tag": "From chaotic orders to order-ready.",
    "video.title": "Ordia in 90 seconds",
  },
};

const I18nContext = createContext(null);

function detectLang() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "it" || stored === "en") return stored;
  } catch { /* ignore */ }
  const nav = (typeof navigator !== "undefined" && (navigator.language || navigator.userLanguage)) || "";
  return nav.toLowerCase().startsWith("it") ? "it" : "en";
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(detectLang);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* ignore */ }
    if (typeof document !== "undefined") document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l) => setLangState(l === "it" ? "it" : "en"), []);
  const t = useCallback((key) => (DICT[lang] && DICT[lang][key]) || DICT.en[key] || key, [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);

export function LanguageToggle({ className = "" }) {
  const { lang, setLang } = useI18n();
  return (
    <div className={`inline-flex items-center rounded-full border border-border bg-white/80 p-0.5 backdrop-blur ${className}`} data-testid="language-toggle">
      <button
        data-testid="lang-it"
        onClick={() => setLang("it")}
        className={`rounded-full px-2.5 py-1 text-sm transition-colors ${lang === "it" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
        aria-label="Italiano"
      >
        🇮🇹
      </button>
      <button
        data-testid="lang-en"
        onClick={() => setLang("en")}
        className={`rounded-full px-2.5 py-1 text-sm transition-colors ${lang === "en" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}
        aria-label="English"
      >
        🇬🇧
      </button>
    </div>
  );
}
