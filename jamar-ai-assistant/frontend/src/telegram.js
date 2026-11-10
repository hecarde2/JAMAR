/**
 * Puente con el SDK de Telegram WebApp.
 *
 * Cuando la interfaz se abre como Mini App, se expone el `user.id` para que el
 * backend comparta la misma sesión que el bot. Fuera de Telegram el objeto
 * devuelve `available: false` y el widget opera como web tradicional.
 */
let cached = null;

export function initTelegram() {
  if (cached) return cached;

  const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;

  if (!tg) {
    cached = { available: false, userId: null, user: null, platform: "web" };
    return cached;
  }

  try {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor("#0B5D3B");
    if (tg.setBackgroundColor) tg.setBackgroundColor("#FAF8F3");
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
  } catch {
    // El SDK puede no estar completamente inicializado; se ignora de forma segura.
  }

  const user = tg.initDataUnsafe?.user || null;

  cached = {
    available: true,
    userId: user ? `tg-${user.id}` : null,
    user,
    platform: tg.platform || "telegram",
    colorScheme: tg.colorScheme,
    webApp: tg,
  };

  return cached;
}

export function hapticFeedback(type = "light") {
  try {
    const tg = window?.Telegram?.WebApp;
    if (!tg?.HapticFeedback) return;
    if (type === "success") tg.HapticFeedback.notificationOccurred("success");
    else if (type === "error") tg.HapticFeedback.notificationOccurred("error");
    else tg.HapticFeedback.impactOccurred(type);
  } catch {
    // Sin soporte de háptica.
  }
}

export function telegramDisplayName(context) {
  if (!context?.user) return null;
  const first = context.user.first_name || "";
  const last = context.user.last_name || "";
  return `${first} ${last}`.trim() || null;
}
