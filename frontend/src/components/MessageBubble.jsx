import {
  ArrowUpRight,
  CalendarClock,
  CheckCircle2,
  Headset,
  Info,
  Palette,
  ScanLine,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import BrandMark from "./BrandMark";
import ProductCard from "./ProductCard";
import { STATUS_LABELS, STATUS_STYLES, cn, formatCop, timeLabel } from "../utils";

const COLOR_HEX = {
  Blanco: "#F2F0EC",
  Crema: "#E8DFCE",
  Beige: "#CDBBA2",
  Gris: "#8A8D8F",
  Negro: "#2B2B2B",
  Madera: "#8B5E3C",
  Nogal: "#7A4E2D",
  Miel: "#B07A3F",
  Verde: "#3F6B52",
  Azul: "#3A5A78",
  Terracota: "#B5654A",
  "Café": "#5E4433",
  Neutro: "#B9B4A8",
};

function AnalysisCard({ analysis }) {
  return (
    <div className="mt-2.5 rounded-xl border border-jamar/15 bg-jamar-mist/70 p-2.5">
      <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-jamar">
        <ScanLine size={12} />
        Análisis del espacio
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        <span className="rounded-md bg-white px-1.5 py-0.5 text-[10px] font-medium text-stone-600 ring-1 ring-stone-200">
          {analysis.room_type}
        </span>
        <span className="rounded-md bg-white px-1.5 py-0.5 text-[10px] font-medium text-stone-600 ring-1 ring-stone-200">
          {analysis.style}
        </span>
      </div>
      {analysis.dominant_colors?.length > 0 && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <Palette size={11} className="text-stone-400" />
          {analysis.dominant_colors.slice(0, 4).map((color) => (
            <span
              key={color}
              className="inline-flex items-center gap-1 rounded-full bg-white px-1.5 py-0.5 text-[9.5px] text-stone-600 ring-1 ring-stone-200"
            >
              <span
                className="h-2 w-2 rounded-full ring-1 ring-stone-200"
                style={{ backgroundColor: COLOR_HEX[color] || "#B9B4A8" }}
              />
              {color}
            </span>
          ))}
        </div>
      )}
      {analysis.notes && <p className="mt-1.5 text-[10.5px] leading-relaxed text-stone-500">{analysis.notes}</p>}
    </div>
  );
}

function AdvisorSummary({ advisor }) {
  return (
    <div className="mt-2.5 rounded-xl border border-jamar/15 bg-jamar-mist/70 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-jamar">
          <Headset size={12} />
          Asesoría
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9.5px] font-semibold",
            advisor.available
              ? "border-jamar/20 bg-jamar-light text-jamar"
              : "border-gold/30 bg-gold-light text-gold-dark",
          )}
        >
          <CalendarClock size={10} />
          {advisor.available ? "Horario abierto" : "Fuera de horario"}
        </span>
      </div>
      <p className="mt-1.5 text-[11.5px] font-semibold text-stone-700">Solicitud {advisor.request_id}</p>
      <p className="mt-0.5 text-[10.5px] leading-relaxed text-stone-500">{advisor.schedule}</p>
      {advisor.available && advisor.closing_at_label && (
        <p className="mt-1 text-[10.5px] text-stone-500">Atención hasta {advisor.closing_at_label}</p>
      )}
      {!advisor.available && advisor.next_opening_label && (
        <p className="mt-1 text-[10.5px] font-medium text-jamar">
          Próxima apertura: {advisor.next_opening_label}
        </p>
      )}
    </div>
  );
}

function CreditSummary({ offer, onAdjust }) {
  return (
    <div className="mt-2.5 rounded-xl border border-stone-200 bg-stone-50 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400">
          CrediJamar
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9.5px] font-semibold",
            STATUS_STYLES[offer.status] || STATUS_STYLES.requiere_validacion,
          )}
        >
          {offer.approved ? <CheckCircle2 size={10} /> : <Info size={10} />}
          {STATUS_LABELS[offer.status] || offer.status}
        </span>
      </div>
      <div className="mt-1.5 flex items-end justify-between gap-2">
        <div>
          <p className="text-base font-bold leading-tight text-jamar">{formatCop(offer.weekly_payment)}</p>
          <p className="text-[9.5px] text-stone-500">
            semanales · {offer.term_weeks} semanas · inicial {formatCop(offer.down_payment)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onAdjust?.({ price: offer.price })}
          className="inline-flex items-center gap-1 rounded-lg border border-stone-200 bg-white px-2 py-1 text-[10px] font-semibold text-stone-600 transition hover:border-jamar/40 hover:text-jamar"
        >
          <SlidersHorizontal size={11} />
          Ajustar
        </button>
      </div>
    </div>
  );
}

/**
 * Renderiza un turno de conversación, incluyendo productos, crédito y análisis visual.
 */
export default function MessageBubble({ message, onCredit, onAdd, onSuggestion }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-up">
        <div className="max-w-[86%]">
          {message.image && (
            <img
              src={message.image}
              alt="Espacio compartido por el usuario"
              className="mb-2 max-h-48 w-full rounded-2xl border border-stone-200 object-cover shadow-soft"
            />
          )}
          {message.text && (
            <div className="rounded-2xl rounded-br-md bg-jamar px-3.5 py-2.5 text-[13px] leading-relaxed text-white shadow-soft">
              {message.text}
            </div>
          )}
          <p className="mt-1 text-right text-[9.5px] text-stone-400">{timeLabel(message.ts)}</p>
        </div>
      </div>
    );
  }

  const sourceLabel =
    message.source === "gemini" || message.source === "gemini_vision"
      ? "IA generativa"
      : message.source === "heuristic"
        ? "Análisis local"
        : message.source === "demo"
          ? "Plantilla local"
          : null;
  const dataSourceLabel =
    message.dataSource === "snowflake"
      ? "Datos Snowflake"
      : message.dataSource === "demo"
        ? "Datos demo"
        : null;

  return (
    <div className="flex items-start gap-2 animate-fade-up">
      <BrandMark size={30} variant="solid" className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div
          className={cn(
            "rounded-2xl rounded-tl-md border bg-white px-3.5 py-2.5 shadow-soft",
            message.isError ? "border-rose-200 bg-rose-50/60" : "border-stone-200/80",
          )}
        >
          <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-stone-700">{message.text}</p>
          {message.analysis && <AnalysisCard analysis={message.analysis} />}
          {message.credit && <CreditSummary offer={message.credit} onAdjust={onCredit} />}
          {message.advisor && <AdvisorSummary advisor={message.advisor} />}
        </div>

        {message.products?.length > 0 && (
          <div className="mt-2.5 grid gap-2.5">
            {message.products.map((product) => (
              <ProductCard key={product.id} product={product} onCredit={onCredit} onAdd={onAdd} />
            ))}
          </div>
        )}

        {message.suggestions?.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {message.suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSuggestion?.(suggestion)}
                className="chip group"
              >
                <Sparkles size={11} className="text-gold" />
                {suggestion}
                <ArrowUpRight
                  size={11}
                  className="text-stone-300 transition group-hover:text-jamar"
                />
              </button>
            ))}
          </div>
        )}

        <div className="mt-1 flex items-center gap-1.5 text-[9.5px] text-stone-400">
          <span>{timeLabel(message.ts)}</span>
          {sourceLabel && (
            <>
              <span className="h-0.5 w-0.5 rounded-full bg-stone-300" />
              <span>{sourceLabel}</span>
            </>
          )}
          {dataSourceLabel && (
            <>
              <span className="h-0.5 w-0.5 rounded-full bg-stone-300" />
              <span>{dataSourceLabel}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
