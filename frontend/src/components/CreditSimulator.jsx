import { useEffect, useState } from "react";
import {
  AlertCircle,
  Calculator,
  CheckCircle2,
  CreditCard,
  Info,
  Loader2,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "../api";
import { STATUS_LABELS, STATUS_STYLES, cn, formatCop } from "../utils";
import { hapticFeedback } from "../telegram";

const TERM_OPTIONS = [8, 12, 16, 24, 36, 52];

function SummaryRow({ label, value, emphasize = false }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-[11.5px] text-stone-500">{label}</span>
      <span className={cn("text-[12px] font-semibold text-stone-800", emphasize && "text-jamar")}>{value}</span>
    </div>
  );
}

/**
 * Simulador CrediJamar con cálculo en tiempo real.
 *
 * El backend determina cuota semanal, cuota mensual, intereses y estado de
 * pre-aprobación según el perfil Customer 360 del usuario.
 */
export default function CreditSimulator({
  open,
  onClose,
  initialPrice = 2_000_000,
  productName = null,
  userId = null,
  onAdvance,
}) {
  const [price, setPrice] = useState(initialPrice);
  const [downPct, setDownPct] = useState(10);
  const [term, setTerm] = useState(24);
  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [view, setView] = useState("weekly");

  useEffect(() => {
    if (open) {
      setPrice(initialPrice || 2_000_000);
      setDownPct(10);
      setTerm(24);
      setOffer(null);
      setError(null);
      setView("weekly");
    }
  }, [open, initialPrice]);

  useEffect(() => {
    if (!open) return undefined;
    const numericPrice = Number(price);
    if (!numericPrice || numericPrice < 50_000) {
      setOffer(null);
      return undefined;
    }

    const downPayment = Math.round((numericPrice * downPct) / 100 / 1000) * 1000;
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.creditCheck({
          price: numericPrice,
          down_payment: downPayment,
          term_weeks: term,
          user_id: userId || null,
        });
        if (!cancelled) setOffer(data);
      } catch (requestError) {
        if (!cancelled) {
          setOffer(null);
          setError(requestError.message || "No fue posible calcular la simulación.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 380);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [open, price, downPct, term, userId]);

  useEffect(() => {
    if (!open) return undefined;
    const handleKey = (event) => {
      if (event.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const numericPrice = Number(price) || 0;
  const downPayment = Math.round((numericPrice * downPct) / 100 / 1000) * 1000;
  const statusTone = offer ? STATUS_STYLES[offer.status] || STATUS_STYLES.requiere_validacion : "";
  const statusLabel = offer ? STATUS_LABELS[offer.status] || offer.status : "";

  const handleAdvance = () => {
    if (!offer) return;
    hapticFeedback("success");
    const message =
      `Quiero continuar con la solicitud de crédito CrediJamar` +
      `${productName ? ` para ${productName}` : ""} por ${formatCop(numericPrice)} ` +
      `con cuota inicial de ${formatCop(downPayment)} y plazo de ${term} semanas.`;
    onAdvance?.(message);
    onClose?.();
  };

  return (
    <div
      className="fixed inset-0 z-[80] flex items-end justify-center bg-stone-950/50 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Simulador CrediJamar"
      onClick={onClose}
    >
      <div
        className="flex max-h-[94vh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl animate-slide-up sm:rounded-3xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center gap-3 border-b border-stone-100 bg-gradient-to-r from-jamar-deep to-jamar px-4 py-3.5 text-white">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/12 ring-1 ring-white/20">
            <Calculator size={18} />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold leading-tight">Simulador CrediJamar</h2>
            <p className="text-[11px] text-white/70">Calcula tu cuota semanal y conoce tu pre-aprobación</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 text-white/80 transition hover:bg-white/10 hover:text-white"
            aria-label="Cerrar simulador"
          >
            <X size={18} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-4 chat-scroll">
          {productName && (
            <div className="mb-3 flex items-center gap-2 rounded-xl bg-jamar-mist px-3 py-2 text-[11.5px] text-jamar">
              <CreditCard size={14} />
              <span className="truncate font-medium">{productName}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="credit-price" className="mb-1.5 block text-[11.5px] font-semibold text-stone-700">
                Valor de la compra
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-stone-400">
                  $
                </span>
                <input
                  id="credit-price"
                  type="number"
                  min="50000"
                  step="50000"
                  value={price}
                  onChange={(event) => setPrice(event.target.value === "" ? "" : Number(event.target.value))}
                  className="field pl-7 font-semibold"
                />
              </div>
              <p className="mt-1 text-[10.5px] text-stone-400">{formatCop(numericPrice)}</p>
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="credit-down" className="text-[11.5px] font-semibold text-stone-700">
                  Cuota inicial
                </label>
                <span className="text-[11.5px] font-semibold text-jamar">
                  {downPct}% · {formatCop(downPayment)}
                </span>
              </div>
              <input
                id="credit-down"
                type="range"
                min="10"
                max="70"
                step="1"
                value={downPct}
                onChange={(event) => setDownPct(Number(event.target.value))}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-stone-200 accent-jamar"
              />
              <div className="mt-1 flex justify-between text-[10px] text-stone-400">
                <span>10%</span>
                <span>70%</span>
              </div>
            </div>

            <div>
              <span className="mb-1.5 block text-[11.5px] font-semibold text-stone-700">Plazo</span>
              <div className="grid grid-cols-6 gap-1.5">
                {TERM_OPTIONS.map((weeks) => (
                  <button
                    key={weeks}
                    type="button"
                    onClick={() => setTerm(weeks)}
                    className={cn(
                      "rounded-lg border px-1 py-2 text-[11px] font-semibold transition",
                      term === weeks
                        ? "border-jamar bg-jamar text-white"
                        : "border-stone-200 bg-white text-stone-600 hover:border-jamar/40 hover:text-jamar",
                    )}
                  >
                    {weeks}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[10px] text-stone-400">Plazo expresado en semanas</p>
            </div>

            <div className="rounded-2xl border border-stone-200 bg-stone-50/60 p-3.5">
              {loading && !offer && (
                <div className="flex items-center justify-center gap-2 py-8 text-[12px] text-stone-500">
                  <Loader2 size={16} className="animate-spin text-jamar" />
                  Calculando tu oferta CrediJamar
                </div>
              )}

              {error && !loading && (
                <div className="flex items-start gap-2 py-2 text-[11.5px] text-rose-700">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {offer && (
                <div className={cn("transition", loading && "opacity-60")}>
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-[10.5px] uppercase tracking-wide text-stone-400">
                        {view === "weekly" ? "Cuota semanal" : "Cuota mensual estimada"}
                      </p>
                      <p className="mt-0.5 text-2xl font-bold tracking-tight text-jamar">
                        {formatCop(view === "weekly" ? offer.weekly_payment : offer.monthly_payment)}
                      </p>
                    </div>
                    <div className="flex rounded-lg border border-stone-200 bg-white p-0.5">
                      {["weekly", "monthly"].map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setView(option)}
                          className={cn(
                            "rounded-md px-2 py-1 text-[10.5px] font-semibold transition",
                            view === option ? "bg-jamar text-white" : "text-stone-500",
                          )}
                        >
                          {option === "weekly" ? "Semanal" : "Mensual"}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="mt-2">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold",
                        statusTone,
                      )}
                    >
                      {offer.approved ? <CheckCircle2 size={11} /> : <Info size={11} />}
                      {statusLabel}
                    </span>
                  </div>

                  <div className="mt-3 divide-y divide-stone-200/70 border-t border-stone-200/70 pt-1">
                    <SummaryRow label="Monto financiado" value={formatCop(offer.financed_amount)} />
                    <SummaryRow label="Cuota inicial" value={formatCop(offer.down_payment)} />
                    <SummaryRow label="Intereses totales" value={formatCop(offer.total_interest)} />
                    <SummaryRow label="Total a pagar" value={formatCop(offer.total_to_pay)} emphasize />
                    <SummaryRow label="Cupo pre-aprobado" value={formatCop(offer.max_amount)} />
                  </div>

                  <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-white px-2.5 py-2 text-[10.5px] leading-relaxed text-stone-500">
                    <ShieldCheck size={13} className="mt-0.5 shrink-0 text-jamar" />
                    {offer.reason}
                  </p>
                </div>
              )}

              {!offer && !loading && !error && (
                <p className="py-6 text-center text-[11.5px] text-stone-500">
                  Ingresa un valor válido para ver tu simulación.
                </p>
              )}
            </div>
          </div>
        </div>

        <footer className="border-t border-stone-100 bg-white px-4 py-3">
          <button
            type="button"
            onClick={handleAdvance}
            disabled={!offer || loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-jamar px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-jamar-deep disabled:cursor-not-allowed disabled:opacity-50"
          >
            <CreditCard size={16} />
            Continuar con un asesor
          </button>
          <p className="mt-2 text-center text-[10px] leading-relaxed text-stone-400">
            {offer?.disclaimer ||
              "Simulación informativa. La aprobación definitiva se confirma al completar la solicitud con un asesor CrediJamar."}
          </p>
        </footer>
      </div>
    </div>
  );
}
