const copFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatCop(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "$ 0";
  return copFormatter.format(Number(value)).replace(/\s/g, " ");
}

export function formatCompactCop(value) {
  const number = Number(value) || 0;
  if (number >= 1_000_000) {
    const millions = number / 1_000_000;
    const formatted = millions % 1 === 0 ? millions.toFixed(0) : millions.toFixed(1);
    return `$ ${formatted} M`;
  }
  if (number >= 1_000) return `$ ${Math.round(number / 1_000)} mil`;
  return formatCop(number);
}

export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function timeLabel(timestamp) {
  try {
    return new Date(timestamp).toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function makeId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const STATUS_LABELS = {
  pre_aprobado: "Pre-aprobado",
  requiere_validacion: "Requiere validación",
  no_aprobado: "No aprobado",
};

export const STATUS_STYLES = {
  pre_aprobado: "bg-jamar-light text-jamar border-jamar/20",
  requiere_validacion: "bg-gold-light text-gold-dark border-gold/30",
  no_aprobado: "bg-rose-50 text-rose-700 border-rose-200",
};

export function productImage(image) {
  return `/products/${image || "sofa.png"}`;
}
