/**
 * Cliente HTTP del Asistente Jamar.
 *
 * En producción nginx sirve el frontend y reenvía /api al backend. En desarrollo
 * Vite aplica el proxy configurado, por lo que el valor por defecto es relativo.
 */
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request(path, { method = "GET", body, isForm = false, signal } = {}) {
  const headers = {};
  let payload = body;

  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: payload,
      signal,
    });
  } catch (error) {
    throw new Error("No fue posible conectar con el asistente. Verifica tu conexión.");
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const detail =
      (data && (data.detail || data.message || data.error)) ||
      (typeof text === "string" && text.trim()) ||
      "Ocurrió un error inesperado.";
    throw new Error(typeof detail === "string" ? detail : "Ocurrió un error inesperado.");
  }

  return data;
}

export const api = {
  health: () => request("/api/health"),
  chat: (payload) => request("/api/chat", { method: "POST", body: payload }),
  vision: (formData) => request("/api/vision", { method: "POST", body: formData, isForm: true }),
  creditCheck: (payload) => request("/api/credit-check", { method: "POST", body: payload }),
  creditConfig: () => request("/api/credit/config"),
  advisorStatus: () => request("/api/advisor/status"),
  advisorRequest: (payload) => request("/api/advisor/request", { method: "POST", body: payload }),
  products: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") query.append(key, value);
    });
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request(`/api/products${suffix}`);
  },
  product: (id, city) => {
    const suffix = city ? `?city=${encodeURIComponent(city)}` : "";
    return request(`/api/products/${encodeURIComponent(id)}${suffix}`);
  },
  cities: () => request("/api/cities"),
  customer: (userId) => request(`/api/customer/${encodeURIComponent(userId)}`),
  history: (sessionId) => request(`/api/chat/history/${encodeURIComponent(sessionId)}`),
  reset: (sessionId, userId) => {
    const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    return request(`/api/chat/history/${encodeURIComponent(sessionId)}${suffix}`, { method: "DELETE" });
  },
};
