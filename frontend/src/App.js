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
import Catalog from "@/pages/Catalog";

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen bg-background" />;
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

function PublicOnly({ children }) {
  const { user, ready, pilotMode } = useAuth();
  if (!ready) return <div className="min-h-screen bg-background" />;
  // In pilot mode the login/register pages stay reachable for preview even
  // when the demo session is active; only redirect in production auth mode.
  if (user && !pilotMode) return <Navigate to="/app" replace />;
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
          <Route path="/app/catalog" element={<Protected><Catalog /></Protected>} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
