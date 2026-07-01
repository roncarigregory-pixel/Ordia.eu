import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  SquaresFour,
  Tray,
  Plus,
  Package,
  GearSix,
  SignOut,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/app", label: "Dashboard", icon: SquaresFour, end: true, testid: "nav-dashboard" },
  { to: "/app/orders", label: "Ordini", icon: Tray, testid: "nav-orders" },
  { to: "/app/catalog", label: "Catalogo", icon: Package, testid: "nav-catalog" },
  { to: "/app/setup", label: "Configurazione", icon: GearSix, testid: "nav-setup" },
];

export function AppShell({ children }) {
  const { user, logout, pilotMode } = useAuth();
  const navigate = useNavigate();

  const initials = (user?.name || "U")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-[240px] shrink-0 flex-col border-r border-border bg-white">
        <div className="flex items-center gap-2 px-6 h-16 border-b border-border">
          <img src="https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/53e400df112bf8342c44b820c9a12de25bc1fc5aae7b0c17c68d6fd4dfa8131a.png" alt="Ordia" className="h-7 w-7 rounded-md object-contain" />
          <span className="font-display font-bold text-lg tracking-[0.18em]">ORDIA</span>
          {pilotMode && (
            <span data-testid="pilot-badge" className="ml-auto rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-700">
              Demo
            </span>
          )}
        </div>

        <div className="px-3 pt-4">
          <button
            data-testid="new-order-cta"
            onClick={() => navigate("/app/new")}
            className="w-full flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-3 py-2.5 text-sm font-medium transition-colors hover:bg-primary/90"
          >
            <Plus size={18} weight="bold" />
            Nuovo Ordine
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={item.testid}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                )
              }
            >
              <item.icon size={20} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 px-2 py-1.5">
            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <button
              data-testid="logout-button"
              onClick={logout}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title={pilotMode ? "Esci dalla demo" : "Esci"}
            >
              <SignOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden flex items-center justify-between h-14 px-4 border-b border-border bg-white">
          <div className="flex items-center gap-2">
            <img src="https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/53e400df112bf8342c44b820c9a12de25bc1fc5aae7b0c17c68d6fd4dfa8131a.png" alt="Ordia" className="h-6 w-6 rounded object-contain" />
            <span className="font-display font-bold tracking-[0.18em]">ORDIA</span>
          </div>
          <button data-testid="new-order-cta-mobile" onClick={() => navigate("/app/new")} className="rounded-md bg-primary text-primary-foreground p-2">
            <Plus size={18} weight="bold" />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1600px] mx-auto w-full p-6 md:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
