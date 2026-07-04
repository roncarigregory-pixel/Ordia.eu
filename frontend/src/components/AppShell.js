import { NavLink, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useI18n, LanguageToggle } from "@/context/I18nContext";
import { api } from "@/lib/api";
import { GlobalSearch } from "@/components/GlobalSearch";
import { OnboardingProvider } from "@/components/Onboarding";
import { LayoutGrid, Inbox, Users, Package, Settings, LogOut, Plus, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

const LOGO = "https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/c2366cbc5b415553f0e7a15df85e794d75397480b11ddc13c97ae35d53d7c3be.png";

const NAV = [
  { to: "/app", label: "Dashboard", short: "Home", icon: LayoutGrid, end: true, testid: "nav-dashboard" },
  { to: "/app/orders", label: "Ordini", short: "Ordini", icon: Inbox, testid: "nav-orders" },
  { to: "/app/notifications", label: "Notifiche", short: "Avvisi", icon: Bell, testid: "nav-notifications" },
  { to: "/app/customers", label: "Clienti", short: "Clienti", icon: Users, testid: "nav-customers" },
  { to: "/app/catalog", label: "Catalogo", short: "Catalogo", icon: Package, testid: "nav-catalog" },
  { to: "/app/setup", label: "Configurazione", short: "Setup", icon: Settings, testid: "nav-setup" },
];

export function AppShell({ children }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [notifCount, setNotifCount] = useState(0);

  useEffect(() => {
    const fetchCount = () => api.get("/notifications/counts").then(({ data }) => setNotifCount(data.open || 0)).catch(() => {});
    fetchCount();
    const t = setInterval(fetchCount, 20000);
    return () => clearInterval(t);
  }, []);

  const initials = (user?.name || "U").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <OnboardingProvider>
    <div className="min-h-screen bg-background flex">
      <aside className="hidden md:flex w-[240px] shrink-0 flex-col border-r border-border bg-white">
        <div className="flex items-center gap-2 px-5 h-16 border-b border-border">
          <img src={LOGO} alt="Ordia" className="h-7 w-7 rounded-md object-contain" />
          <span className="font-display font-bold text-lg tracking-[0.18em]">ORDIA</span>
        </div>

        <div className="px-3 pt-4 space-y-3">
          <button
            data-testid="new-order-cta"
            onClick={() => navigate("/app/new")}
            className="w-full flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-3 py-2.5 text-sm font-semibold transition-colors hover:bg-primary/90"
          >
            <Plus size={18} /> {t("Nuovo Ordine")}
          </button>
          <GlobalSearch />
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
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                )
              }
            >
              <item.icon size={19} />
              {t(item.label)}
              {item.to === "/app/notifications" && notifCount > 0 && (
                <span data-testid="notif-badge" className="ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-full bg-red-500 px-1.5 text-[11px] font-bold text-white">{notifCount}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 px-2 py-1.5">
            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold">{initials}</div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <button data-testid="logout-button" onClick={logout} className="text-muted-foreground hover:text-foreground transition-colors" title={t("Esci")}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Desktop top bar — language switcher always visible top-right */}
        <header className="hidden md:flex items-center justify-end h-12 px-6 border-b border-border bg-white/70 backdrop-blur">
          <LanguageToggle />
        </header>
        <header className="md:hidden flex items-center justify-between h-14 px-4 border-b border-border bg-white">
          <div className="flex items-center gap-2">
            <img src={LOGO} alt="Ordia" className="h-6 w-6 rounded object-contain" />
            <span className="font-display font-bold tracking-[0.18em]">ORDIA</span>
          </div>
          <div className="flex items-center gap-2">
            <LanguageToggle />
            <button data-testid="new-order-cta-mobile" onClick={() => navigate("/app/new")} className="rounded-lg bg-primary text-primary-foreground p-2">
              <Plus size={18} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1600px] mx-auto w-full p-6 md:p-8 pb-32 md:pb-8">{children}</div>
        </main>
        {/* Mobile bottom nav — lifted above the platform badge */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 z-[60] flex items-stretch border-t border-border bg-white/95 backdrop-blur pt-1.5 pb-14">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={`${item.testid}-mobile`}
              className={({ isActive }) =>
                cn("relative flex flex-1 flex-col items-center gap-0.5 px-1 py-1 text-[10px] font-medium",
                  isActive ? "text-primary" : "text-muted-foreground")
              }
            >
              <item.icon size={20} />
              {t(item.short)}
              {item.to === "/app/notifications" && notifCount > 0 && (
                <span className="absolute top-0 right-1/4 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">{notifCount}</span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
    </OnboardingProvider>
  );
}
