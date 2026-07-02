import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Auth uses an HttpOnly cookie set by the backend. `withCredentials` ensures the
// cookie travels with every request. No token is persisted in localStorage (XSS-safe).
export const api = axios.create({ baseURL: API, withCredentials: true });

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message || "Something went wrong.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  return String(detail);
}

export { API };
