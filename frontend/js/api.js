/**
 * Minimal fetch-based API client for the ARC Asset Management FastAPI backend.
 * Handles JWT storage/attachment and centralizes error handling.
 */
const API = (() => {
  // Change this if the backend runs on a different host/port.
  const BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";
  const TOKEN_KEY = "arc_access_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  function isAuthenticated() {
    return Boolean(getToken());
  }

  /**
   * Core request helper. Automatically attaches the JWT (unless skipAuth),
   * serializes JSON bodies, and throws a readable Error on failure.
   */
  async function request(path, { method = "GET", body, isForm = false, skipAuth = false } = {}) {
    const headers = {};
    if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";
    if (!skipAuth) {
      const token = getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });

    if (response.status === 401) {
      clearToken();
      window.dispatchEvent(new CustomEvent("auth:expired"));
      throw new Error("Session expired. Please log in again.");
    }

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const errJson = await response.json();
        detail = errJson.detail ? formatDetail(errJson.detail) : detail;
      } catch (_) {
        /* response had no JSON body */
      }
      throw new Error(detail);
    }

    if (response.status === 204) return null;

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) return response.json();
    return response.blob();
  }

  function formatDetail(detail) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    }
    return JSON.stringify(detail);
  }

  function buildQuery(params) {
    const query = Object.entries(params || {})
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    return query ? `?${query}` : "";
  }

  return {
    // Auth
    login: (email, password) =>
      request("/auth/login", { method: "POST", body: { email, password }, skipAuth: true }),
    register: (email, password) =>
      request("/auth/register", { method: "POST", body: { email, password }, skipAuth: true }),
    logout: () => clearToken(),
    setToken,
    getToken,
    isAuthenticated,

    // Assets
    listAssets: (filters) => request(`/assets${buildQuery(filters)}`),
    createAsset: (payload) => request("/assets", { method: "POST", body: payload }),
    updateAsset: (id, payload) => request(`/assets/${id}`, { method: "PUT", body: payload }),
    deleteAsset: (id) => request(`/assets/${id}`, { method: "DELETE" }),
    uploadCsv: (file) => {
      const form = new FormData();
      form.append("file", file);
      return request("/assets/upload-csv", { method: "POST", body: form, isForm: true });
    },
    stickerUrl: (id) => `${BASE_URL}/assets/${id}/generate-sticker`,
    fetchSticker: async (id) => {
      const token = getToken();
      const response = await fetch(`${BASE_URL}/assets/${id}/generate-sticker`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Failed to generate sticker");
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    },
  };
})();
