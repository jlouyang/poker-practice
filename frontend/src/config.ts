// Empty VITE_API_URL (e.g. in production Docker) = same-origin. Unset = dev default localhost:8000.
const _api = import.meta.env.VITE_API_URL;
export const API_URL =
  _api === "" ? "" : (_api || "http://localhost:8000");
export const WS_URL = API_URL ? API_URL.replace(/^http/, "ws") : "";
