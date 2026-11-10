import { cn } from "../utils";

/**
 * Marca gráfica de Jamar usada en el header, el hero y los mensajes del asistente.
 */
export default function BrandMark({ size = 40, variant = "solid", className }) {
  const isSolid = variant === "solid";
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-xl",
        isSolid ? "bg-white/12 ring-1 ring-white/25" : "bg-jamar text-white ring-1 ring-jamar/10",
        className,
      )}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 40 40" width={size * 0.62} height={size * 0.62} fill="none">
        <path
          d="M13 8h6v17.2c0 4.3-2.8 6.8-6.9 6.8-2.7 0-4.8-1-6.1-2.5l2.8-3.5c.7.8 1.7 1.3 2.9 1.3 1.6 0 2.3-.8 2.3-2.5V8Z"
          fill={isSolid ? "#FFFFFF" : "#FFFFFF"}
        />
        <circle cx="29.5" cy="29.5" r="3.2" fill="#C9A227" />
        <path d="M24 8h6v6h-6z" fill={isSolid ? "#C9A227" : "#C9A227"} opacity="0.9" />
      </svg>
    </span>
  );
}
