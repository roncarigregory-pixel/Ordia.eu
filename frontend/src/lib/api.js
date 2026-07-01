import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ordia_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
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
