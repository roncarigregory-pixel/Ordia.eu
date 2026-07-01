import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

// --- Pilot mode ---------------------------------------------------------
// During the pilot, users land directly inside the product on a seeded demo
// workspace. To switch real authentication back on for production, set
// REACT_APP_PILOT_MODE=false in the frontend .env (no code changes needed).
export const PILOT_MODE = process.env.REACT_APP_PILOT_MODE !== "false";
const DEMO_EMAIL = process.env.REACT_APP_DEMO_EMAIL || "demo@ordia.app";
const DEMO_PASSWORD = process.env.REACT_APP_DEMO_PASSWORD || "demo123";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = logged out, object = logged in
  const [ready, setReady] = useState(false);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem("ordia_token");
    if (token) {
      try {
        const { data } = await api.get("/auth/me");
        setUser(data);
        setReady(true);
        return;
      } catch {
        localStorage.removeItem("ordia_token");
      }
    }
    // No valid session — in pilot mode auto-enter the demo workspace.
    if (PILOT_MODE) {
      try {
        const { data } = await api.post("/auth/login", { email: DEMO_EMAIL, password: DEMO_PASSWORD });
        localStorage.setItem("ordia_token", data.access_token);
        setUser(data.user);
      } catch {
        setUser(false);
      }
    } else {
      setUser(false);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("ordia_token", data.access_token);
    setUser(data.user);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    localStorage.setItem("ordia_token", data.access_token);
    setUser(data.user);
  };

  const logout = () => {
    localStorage.removeItem("ordia_token");
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout, pilotMode: PILOT_MODE }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
