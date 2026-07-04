import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "@phosphor-icons/react";
import { useI18n } from "@/context/I18nContext";

export function SetupBack({ label = "Configurazione", to = "/app/setup" }) {
  const navigate = useNavigate();
  const { t } = useI18n();
  return (
    <button
      data-testid="setup-back"
      onClick={() => navigate(to)}
      className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4"
    >
      <ArrowLeft size={16} /> {t(label)}
    </button>
  );
}

export function Field({ label, hint, children, testid }) {
  return (
    <div data-testid={testid}>
      <label className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">{label}</label>
      <div className="mt-1.5">{children}</div>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export const inputCls =
  "w-full rounded-md border border-input bg-white px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ring";
