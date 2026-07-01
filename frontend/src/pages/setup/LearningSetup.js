import { useEffect, useState, useCallback } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { SetupBack } from "./_shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Brain, Trash, MagnifyingGlass } from "@phosphor-icons/react";

export default function LearningSetup() {
  const [items, setItems] = useState(null);
  const [q, setQ] = useState("");

  const load = useCallback(() => api.get("/learning").then(({ data }) => setItems(data)).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);

  const remove = async (it) => {
    try { await api.delete(`/learning/${it.id}`); load(); toast.success("Regola rimossa"); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  const filtered = (items || []).filter((i) =>
    !q || i.phrase.includes(q.toLowerCase()) || (i.name || "").toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="animate-fade-up max-w-3xl">
      <SetupBack />
      <div className="flex items-center gap-3 mb-6">
        <div className="h-11 w-11 rounded-md bg-secondary flex items-center justify-center"><Brain size={22} /></div>
        <div>
          <h1 className="font-display text-3xl font-black tracking-tighter">Apprendimento</h1>
          <p className="text-sm text-muted-foreground">Ogni ordine validato insegna a Ordia. Queste regole migliorano i prossimi abbinamenti.</p>
        </div>
      </div>

      <div className="relative max-w-xs mb-4">
        <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input data-testid="learning-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cerca frase o prodotto…" className="w-full rounded-md border border-input bg-white pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
      </div>

      <div className="rounded-md border border-border bg-white overflow-hidden">
        {!items ? (
          <div className="p-4 space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 rounded-md" />)}</div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center">
            <Brain size={36} className="mx-auto text-slate-300" />
            <p className="mt-3 text-sm text-muted-foreground">Ancora nessuna regola appresa. Valida qualche ordine e Ordia inizierà a imparare.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">Frase cliente</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground">→ Prodotto</th>
                <th className="px-5 py-3 text-xs font-medium uppercase tracking-[0.15em] text-muted-foreground text-center">Volte</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((it) => (
                <tr key={it.id} data-testid={`learning-row-${it.id}`} className="hover:bg-secondary/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs">"{it.phrase}"</td>
                  <td className="px-5 py-3 font-medium">{it.name} <span className="text-xs text-muted-foreground font-mono">{it.sku}</span></td>
                  <td className="px-5 py-3 text-center font-mono text-muted-foreground">{it.count}</td>
                  <td className="px-5 py-3 text-right">
                    <button data-testid={`learning-delete-${it.id}`} onClick={() => remove(it)} className="text-slate-300 hover:text-red-500"><Trash size={16} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
