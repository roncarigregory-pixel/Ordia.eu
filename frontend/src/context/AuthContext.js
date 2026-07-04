import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api, setAuthToken } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = logged out, object = logged in
  const [ready, setReady] = useState(false);

  const loadUser = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me", { timeout: 12000 });
      setUser(data);
    } catch {
      setUser(false); // no valid session
    }
    setReady(true);
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setAuthToken(data.access_token);
    setUser(data.user);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    setAuthToken(data.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch { /* ignore logout errors */ }
    setAuthToken(null);
    setUser(false);
  };

  const value = useMemo(
    () => ({ user, ready, login, register, logout }),
    [user, ready]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
