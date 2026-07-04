import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/context/I18nContext";
import { formatApiError } from "@/lib/api";
import { ArrowRight, Sparkle } from "@phosphor-icons/react";

const WAREHOUSE = "https://images.pexels.com/photos/4481327/pexels-photo-4481327.jpeg";

export default function Login() {
  const { login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/app");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <div className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="flex items-center gap-2 mb-10">
            <img src="https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/c2366cbc5b415553f0e7a15df85e794d75397480b11ddc13c97ae35d53d7c3be.png" alt="Ordia" className="h-8 w-8 rounded-md object-contain" />
            <span className="font-display font-bold text-xl tracking-[0.18em]">ORDIA</span>
          </div>

          <h1 className="font-display text-3xl font-black tracking-tighter mb-1">{t("Bentornato")}</h1>
          <p className="text-sm text-muted-foreground mb-8">{t("Accedi al tuo centro di comando ordini.")}</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Email")}</label>
              <input
                data-testid="login-email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring focus:ring-offset-0"
                placeholder={t("tu@azienda.com")}
              />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{t("Password")}</label>
              <input
                data-testid="login-password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p data-testid="login-error" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <button
              data-testid="login-submit-button"
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium transition-colors hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? t("Accesso in corso…") : t("Accedi")}
              {!loading && <ArrowRight size={16} weight="bold" />}
            </button>
          </form>

          <p className="mt-6 text-sm text-muted-foreground">
            {t("Nuovo su Ordia?")}{" "}
            <Link data-testid="go-to-register" to="/register" className="font-medium text-foreground underline underline-offset-4">
              {t("Crea un account")}
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
            {t("Basta riscrivere gli ordini a mano.")}
          </h2>
          <p className="mt-3 text-sm text-white/70 max-w-md leading-relaxed">
            {t("Ordia legge gli ordini da WhatsApp, email, PDF, fogli di calcolo e foto — poi estrae, abbina e valida automaticamente. Tu devi solo confermare.")}
          </p>
        </div>
      </div>
    </div>
  );
}
