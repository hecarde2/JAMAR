import { MessageCircle } from "lucide-react";
import { cn } from "../utils";

/**
 * Botón flotante que abre el widget en web y móvil.
 */
export default function Launcher({ onClick, cartCount = 0, className }) {
  return (
    <div className={cn("fixed bottom-5 right-5 z-40 flex items-center gap-3 sm:bottom-6 sm:right-6", className)}>
      <span className="hidden rounded-full border border-stone-200 bg-white/95 px-3 py-1.5 text-xs font-medium text-stone-600 shadow-soft backdrop-blur sm:block">
        Asesoría Jamar en línea
      </span>
      <button
        type="button"
        onClick={onClick}
        className="group relative flex h-14 w-14 items-center justify-center rounded-full bg-jamar text-white shadow-widget transition hover:bg-jamar-deep focus:outline-none focus-visible:ring-4 focus-visible:ring-jamar/30"
        aria-label="Abrir el Asistente Jamar"
      >
        <span className="absolute inset-0 -z-10 rounded-full bg-jamar/40 animate-pulse-ring" aria-hidden="true" />
        <MessageCircle size={24} strokeWidth={1.8} />
        <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-white bg-gold px-1 text-[10px] font-bold text-white">
          {cartCount > 0 ? (cartCount > 9 ? "9+" : cartCount) : ""}
          {cartCount === 0 && <span className="h-1.5 w-1.5 rounded-full bg-white" />}
        </span>
      </button>
    </div>
  );
}
