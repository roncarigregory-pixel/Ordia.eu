import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Auth: the backend sets an HttpOnly cookie (used in production / same-origin).
// Because the preview runs inside a cross-site iframe where third-party cookies
// may be blocked, we ALSO keep the JWT in memory (never localStorage) and send it
// as a Bearer header. In-memory = XSS-safer than localStorage (not persisted).
let _authToken = null;
export function setAuthToken(token) {
  _authToken = token || null;
}

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  if (_authToken) config.headers.Authorization = `Bearer ${_authToken}`;
  return config;
});

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message || "Something went wrong.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  return String(detail);
}

export { API };
