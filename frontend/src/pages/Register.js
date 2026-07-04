import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/context/I18nContext";
import { formatApiError } from "@/lib/api";
import { ArrowRight, Sparkle } from "@phosphor-icons/react";

const WAREHOUSE = "https://images.pexels.com/photos/4481327/pexels-photo-4481327.jpeg";

export default function Register() {
  const { register } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [form, setForm] = useState({ company_name: "", name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(form);
      navigate("/app");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const field = (key, label, type = "text", placeholder = "") => (
    <div>
      <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{label}</label>
      <input
        data-testid={`register-${key}-input`}
        type={type}
        required
        value={form[key]}
        onChange={set(key)}
        placeholder={placeholder}
        className="mt-1.5 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
      />
    </div>
  );

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="flex items-center gap-2 mb-8">
            <img src="https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/c2366cbc5b415553f0e7a15df85e794d75397480b11ddc13c97ae35d53d7c3be.png" alt="Ordia" className="h-8 w-8 rounded-md object-contain" />
            <span className="font-display font-bold text-xl tracking-[0.18em]">ORDIA</span>
          </div>

          <h1 className="font-display text-3xl font-black tracking-tighter mb-1">{t("Crea il tuo spazio")}</h1>
          <p className="text-sm text-muted-foreground mb-6">
            {t("Include un catalogo per grossisti alimentari già pronto, per provare subito l'estrazione.")}
          </p>

          <form onSubmit={submit} className="space-y-4">
            {field("company_name", t("Azienda"), "text", "Fresh Foods Ingrosso")}
            {field("name", t("Il tuo nome"), "text", "Alessandro Rossi")}
            {field("email", t("Email"), "email", "tu@azienda.com")}
            {field("password", t("Password"), "password", t("Almeno 6 caratteri"))}

            {error && (
              <p data-testid="register-error" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <button
              data-testid="register-submit-button"
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium transition-colors hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? t("Creazione…") : t("Crea spazio di lavoro")}
              {!loading && <ArrowRight size={16} weight="bold" />}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted-foreground">
            {t("Hai già un account?")}{" "}
            <Link data-testid="go-to-login" to="/login" className="font-medium text-foreground underline underline-offset-4">
              {t("Accedi")}
            </Link>
          </p>
        </div>
      </div>

      <div className="hidden lg:block relative">
        <img src={WAREHOUSE} alt="Magazzino" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-slate-950/80" />
        <div className="absolute inset-0 flex flex-col justify-end p-12 text-white">
          <Sparkle size={28} weight="fill" className="mb-4 opacity-80" />
          <h2 className="font-display text-3xl font-black tracking-tight leading-tight max-w-md">
            {t("Il sistema operativo per la gestione ordini.")}
          </h2>
          <p className="mt-3 text-sm text-white/70 max-w-md leading-relaxed">
            {t("Ogni correzione dell'operatore insegna a Ordia. Impara i tuoi clienti, le loro abitudini e le loro abbreviazioni — e non ripete mai un errore.")}
          </p>
        </div>
      </div>
    </div>
  );
}
