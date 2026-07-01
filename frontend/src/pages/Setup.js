import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import {
  WhatsappLogo, EnvelopeSimple, Package, Plugs, UsersThree, Buildings,
  CheckCircle, CaretRight, Circle,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

const CARDS = [
  { key: "company", to: "/app/setup/company", icon: Buildings, title: "Dati azienda", desc: "Ragione sociale, P.IVA, valuta e recapiti." },
  { key: "catalog", to: "/app/catalog", icon: Package, title: "Catalogo prodotti", desc: "Prodotti, alias e formati per l'abbinamento AI." },
  { key: "whatsapp", to: "/app/setup/whatsapp", icon: WhatsappLogo, title: "WhatsApp Business", desc: "Ricevi ordini direttamente dai tuoi clienti." },
  { key: "email", to: "/app/setup/email", icon: EnvelopeSimple, title: "Email", desc: "Casella dedicata o la tua email aziendale." },
  { key: "erp", to: "/app/setup/erp", icon: Plugs, title: "Export ERP", desc: "Webhook, REST, JSON, CSV, XML — ERP-agnostico." },
  { key: "team", to: "/app/setup/team", icon: UsersThree, title: "Team", desc: "Invita colleghi e assegna i ruoli." },
];

export default function Setup() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/integrations").then(({ data }) => setData(data)).catch(() => {});
  }, []);

  const stepByKey = (k) => data?.steps.find((s) => s.key === k);

  return (
    <div className="animate-fade-up max-w-5xl">
      <h1 className="font-display text-4xl font-black tracking-tighter">Configurazione</h1>
      <p className="mt-1 text-sm text-muted-foreground mb-8">
        Il tuo consulente tecnico integrato. Collega i canali d'ordine e l'ERP passo dopo passo.
      </p>

      {!data ? (
        <Skeleton className="h-24 rounded-md mb-8" />
      ) : (
        <div className="rounded-md border border-border bg-white p-6 mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Avanzamento setup</span>
            <span data-testid="setup-progress" className="font-mono text-sm font-medium">{data.completed}/{data.total} · {data.progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-secondary overflow-hidden">
            <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${data.progress}%` }} />
          </div>
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
            {data.steps.map((s) => (
              <div key={s.key} className="flex items-center gap-1.5 text-sm">
                {s.done ? <CheckCircle size={16} weight="fill" className="text-emerald-500" /> : <Circle size={16} className="text-slate-300" />}
                <span className={cn(s.done ? "text-foreground" : "text-muted-foreground")}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {CARDS.map((c) => {
          const step = stepByKey(c.key);
          const status = step?.status;
          return (
            <button
              key={c.key}
              data-testid={`setup-card-${c.key}`}
              onClick={() => navigate(c.to)}
              className="group flex items-start gap-4 rounded-md border border-border bg-white p-5 text-left transition-colors hover:border-slate-300"
            >
              <div className="h-11 w-11 shrink-0 rounded-md bg-secondary flex items-center justify-center">
                <c.icon size={22} className="text-slate-700" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-display font-bold tracking-tight">{c.title}</h3>
                  {step?.done && <CheckCircle size={16} weight="fill" className="text-emerald-500" />}
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">{c.desc}</p>
                {status && status !== "not_configured" && (
                  <div className="mt-2"><StatusBadge status={status === "connected" ? "validated" : status === "error" ? "needs_review" : "ready"} /></div>
                )}
              </div>
              <CaretRight size={18} className="text-slate-300 group-hover:text-slate-500 transition-colors mt-1" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
