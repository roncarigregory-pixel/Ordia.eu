import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { toast } from "sonner";
import { SetupBack, Field, inputCls } from "./_shared";
import { Buildings } from "@phosphor-icons/react";

const CURRENCIES = ["EUR", "USD", "GBP", "CHF"];

export default function CompanySetup() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const { t } = useI18n();

  useEffect(() => {
    api.get("/company").then(({ data }) => setForm({
      name: data.name || "", vat: data.vat || "", address: data.address || "",
      country: data.country || "", currency: data.currency || "EUR", phone: data.phone || "",
    })).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/company", form);
      toast.success(t("Dati azienda salvati"));
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  if (!form) return null;

  return (
    <div className="animate-fade-up max-w-2xl">
      <SetupBack />
      <div className="flex items-center gap-3 mb-6">
        <div className="h-11 w-11 rounded-md bg-secondary flex items-center justify-center"><Buildings size={22} /></div>
        <div>
          <h1 className="font-display text-3xl font-black tracking-tighter">{t("Dati azienda")}</h1>
          <p className="text-sm text-muted-foreground">{t("Compaiono su export ed email in uscita.")}</p>
        </div>
      </div>

      <div className="rounded-md border border-border bg-white p-6 space-y-4">
        <Field label={t("Ragione sociale")} testid="company-name">
          <input value={form.name} onChange={set("name")} className={inputCls} />
        </Field>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("Partita IVA")} testid="company-vat">
            <input value={form.vat} onChange={set("vat")} placeholder="IT01234567890" className={inputCls} />
          </Field>
          <Field label={t("Telefono")} testid="company-phone">
            <input value={form.phone} onChange={set("phone")} className={inputCls} />
          </Field>
        </div>
        <Field label={t("Indirizzo")} testid="company-address">
          <input value={form.address} onChange={set("address")} className={inputCls} />
        </Field>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label={t("Paese")} testid="company-country">
            <input value={form.country} onChange={set("country")} placeholder="Italia" className={inputCls} />
          </Field>
          <Field label={t("Valuta")} testid="company-currency">
            <select value={form.currency} onChange={set("currency")} className={inputCls}>
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
        </div>
        <div className="pt-2">
          <button data-testid="company-save" onClick={save} disabled={saving} className="rounded-md bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-60">
            {saving ? t("Salvataggio…") : t("Salva")}
          </button>
        </div>
      </div>
    </div>
  );
}
