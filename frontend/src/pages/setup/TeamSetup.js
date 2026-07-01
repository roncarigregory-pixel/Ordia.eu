import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack, Field, inputCls } from "./_shared";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { UsersThree, Plus, Trash } from "@phosphor-icons/react";

const ROLES = [
  { key: "owner", label: "Owner", desc: "Controllo totale" },
  { key: "admin", label: "Admin", desc: "Gestione completa" },
  { key: "sales", label: "Sales", desc: "Ordini e clienti" },
  { key: "operator", label: "Order Operator", desc: "Valida ed estrae ordini" },
  { key: "warehouse", label: "Warehouse", desc: "Consegne e magazzino" },
  { key: "readonly", label: "Read Only", desc: "Sola lettura" },
];
const roleLabel = (k) => ROLES.find((r) => r.key === k)?.label || k;

export default function TeamSetup() {
  const [members, setMembers] = useState(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "operator" });

  const load = useCallback(() => api.get("/team").then(({ data }) => setMembers(data)).catch(() => setMembers([])), []);
  useEffect(() => { load(); }, [load]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const add = async () => {
    if (!form.name || !form.email || form.password.length < 6) return toast.error("Compila nome, email e password (min 6).");
    try {
      await api.post("/team", form);
      toast.success("Membro aggiunto");
      setOpen(false);
      setForm({ name: "", email: "", password: "", role: "operator" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const changeRole = async (m, role) => {
    try { await api.put(`/team/${m.id}/role`, { role }); load(); toast.success("Ruolo aggiornato"); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  const remove = async (m) => {
    try { await api.delete(`/team/${m.id}`); load(); toast.success("Membro rimosso"); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div className="animate-fade-up max-w-3xl">
      <SetupBack />
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-md bg-secondary flex items-center justify-center"><UsersThree size={22} /></div>
          <div>
            <h1 className="font-display text-3xl font-black tracking-tighter">Team</h1>
            <p className="text-sm text-muted-foreground">Accesso multi-tenant: ognuno vede solo i dati della propria azienda.</p>
          </div>
        </div>
        <button data-testid="team-add-button" onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium hover:bg-primary/90">
          <Plus size={18} weight="bold" /> Aggiungi
        </button>
      </div>

      <div className="rounded-md border border-border bg-white overflow-hidden">
        {members?.map((m) => (
          <div key={m.id} data-testid={`team-row-${m.id}`} className="flex items-center gap-4 px-5 py-3.5 border-b border-border last:border-0">
            <div className="h-9 w-9 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold">
              {(m.name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{m.name}</p>
              <p className="text-xs text-muted-foreground truncate">{m.email}</p>
            </div>
            <select
              data-testid={`team-role-${m.id}`}
              value={m.role}
              onChange={(e) => changeRole(m, e.target.value)}
              disabled={m.role === "owner"}
              className="rounded-md border border-input bg-white px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
            >
              {ROLES.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
            </select>
            {m.role !== "owner" && (
              <button data-testid={`team-delete-${m.id}`} onClick={() => remove(m)} className="text-slate-300 hover:text-red-500"><Trash size={16} /></button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-md border border-border bg-white p-5">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground mb-3">Ruoli disponibili</p>
        <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
          {ROLES.map((r) => (
            <div key={r.key} className="flex items-baseline gap-2 text-sm">
              <span className="font-medium">{r.label}</span>
              <span className="text-muted-foreground text-xs">— {r.desc}</span>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle className="font-display tracking-tight">Aggiungi membro</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Field label="Nome" testid="member-name"><input value={form.name} onChange={set("name")} className={inputCls} /></Field>
            <Field label="Email" testid="member-email"><input type="email" value={form.email} onChange={set("email")} className={inputCls} /></Field>
            <Field label="Password" testid="member-password"><input type="password" value={form.password} onChange={set("password")} className={inputCls} /></Field>
            <Field label="Ruolo" testid="member-role">
              <select value={form.role} onChange={set("role")} className={inputCls}>
                {ROLES.filter((r) => r.key !== "owner").map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
              </select>
            </Field>
          </div>
          <DialogFooter>
            <button onClick={() => setOpen(false)} className="rounded-md border border-input bg-white px-4 py-2 text-sm font-medium hover:bg-secondary">Annulla</button>
            <button data-testid="member-save" onClick={add} className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90">Aggiungi</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
