import { useState } from "react";
import PhoneInput from "react-phone-number-input";
import "react-phone-number-input/style.css";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

// Global-first early-access capture: international phone, GDPR consent, locale + source tracked.
export function EarlyAccessForm({ onRegister }) {
  const { t, lang } = useI18n();
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!consent) return toast.error(t("Devi accettare per proseguire."));
    setBusy(true);
    try {
      const params = new URLSearchParams(window.location.search);
      const source = params.get("utm_source") || params.get("ref") || document.referrer || "direct";
      await api.post("/leads", {
        email, company_name: company, phone, consent,
        locale: lang || "en", source: String(source).slice(0, 300),
      });
      setDone(true);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div data-testid="early-access-success" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-center">
        <CheckCircle2 className="mx-auto text-emerald-500" size={40} />
        <h3 className="mt-3 font-display text-xl font-bold text-emerald-900">{t("Ci sei! Sei nella lista.")}</h3>
        <p className="mx-auto mt-1 max-w-md text-sm text-emerald-800">{t("Ti abbiamo inviato una conferma via email. Vuoi provarlo subito?")}</p>
        <button
          data-testid="early-access-to-register"
          onClick={onRegister}
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.03]"
        >
          {t("Crea il tuo account e prova ora")} <ArrowRight size={16} />
        </button>
      </div>
    );
  }

  return (
    <form data-testid="early-access-form" onSubmit={submit} className="mx-auto max-w-md space-y-3 text-left">
      <input
        data-testid="early-access-email" type="email" required value={email}
        onChange={(e) => setEmail(e.target.value)} placeholder={t("Email di lavoro")}
        className="w-full rounded-xl border border-input bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-ring"
      />
      <input
        data-testid="early-access-company" value={company}
        onChange={(e) => setCompany(e.target.value)} placeholder={t("Nome azienda (opzionale)")}
        className="w-full rounded-xl border border-input bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-ring"
      />
      <div className="rounded-xl border border-input bg-white px-3 py-2.5">
        <PhoneInput
          data-testid="early-access-phone" international defaultCountry="IT"
          value={phone} onChange={(v) => setPhone(v || "")}
          placeholder={t("Telefono (opzionale)")}
        />
      </div>
      <label data-testid="early-access-consent" className="flex items-start gap-2 text-left text-xs text-muted-foreground">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
        <span>{t("consent.marketing")}</span>
      </label>
      <button
        data-testid="early-access-submit" type="submit" disabled={busy}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.02] disabled:opacity-60"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
        {t("Richiedi accesso anticipato")}
      </button>
    </form>
  );
}
