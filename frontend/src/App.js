import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AppShell } from "@/components/AppShell";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import NewOrder from "@/pages/NewOrder";
import Orders from "@/pages/Orders";
import OrderReview from "@/pages/OrderReview";
import NotificationCenter from "@/pages/NotificationCenter";
import Customers from "@/pages/Customers";
import CustomerDetail from "@/pages/CustomerDetail";
import Catalog from "@/pages/Catalog";
import Setup from "@/pages/Setup";
import WhatsAppSetup from "@/pages/setup/WhatsAppSetup";
import EmailSetup from "@/pages/setup/EmailSetup";
import ErpSetup from "@/pages/setup/ErpSetup";
import TeamSetup from "@/pages/setup/TeamSetup";
import CompanySetup from "@/pages/setup/CompanySetup";
import LearningSetup from "@/pages/setup/LearningSetup";
import AutomationSetup from "@/pages/setup/AutomationSetup";

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4" data-testid="app-loading">
      <img
        src="https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/c2366cbc5b415553f0e7a15df85e794d75397480b11ddc13c97ae35d53d7c3be.png"
        alt="Ordia"
        className="h-12 w-12 rounded-xl object-contain animate-pulse"
      />
      <div className="h-1 w-32 overflow-hidden rounded-full bg-secondary">
        <div className="h-full w-1/2 rounded-full bg-primary animate-pulse" />
      </div>
      <p className="text-sm text-muted-foreground">Caricamento di Ordia…</p>
    </div>
  );
}

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function PublicOnly({ children }) {
  const { user, ready, pilotMode } = useAuth();
  // Public pages render immediately; redirect only once we KNOW a prod user is logged in.
  if (ready && user && !pilotMode) return <Navigate to="/app" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-center" richColors />
        <Routes>
          <Route path="/" element={<Navigate to="/app" replace />} />
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
          <Route path="/app" element={<Protected><Dashboard /></Protected>} />
          <Route path="/app/new" element={<Protected><NewOrder /></Protected>} />
          <Route path="/app/orders" element={<Protected><Orders /></Protected>} />
          <Route path="/app/orders/:id" element={<Protected><OrderReview /></Protected>} />
          <Route path="/app/notifications" element={<Protected><NotificationCenter /></Protected>} />
          <Route path="/app/customers" element={<Protected><Customers /></Protected>} />
          <Route path="/app/customers/:name" element={<Protected><CustomerDetail /></Protected>} />
          <Route path="/app/catalog" element={<Protected><Catalog /></Protected>} />
          <Route path="/app/setup" element={<Protected><Setup /></Protected>} />
          <Route path="/app/setup/whatsapp" element={<Protected><WhatsAppSetup /></Protected>} />
          <Route path="/app/setup/email" element={<Protected><EmailSetup /></Protected>} />
          <Route path="/app/setup/erp" element={<Protected><ErpSetup /></Protected>} />
          <Route path="/app/setup/team" element={<Protected><TeamSetup /></Protected>} />
          <Route path="/app/setup/company" element={<Protected><CompanySetup /></Protected>} />
          <Route path="/app/setup/learning" element={<Protected><LearningSetup /></Protected>} />
          <Route path="/app/setup/automations" element={<Protected><AutomationSetup /></Protected>} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
