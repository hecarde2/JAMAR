import { useEffect, useRef, useState } from "react";
import {
  Download,
  Loader2,
  Move,
  RotateCcw,
  RotateCw,
  X,
  ZoomIn,
} from "lucide-react";
import { api } from "../api";
import { cn, productImage } from "../utils";

const DEFAULT_TRANSFORM = { x: 50, y: 68, scale: 0.45, rotation: 0 };

export default function PhotoComposer({ photo, product, onClose, onSave, onError }) {
  const [transform, setTransform] = useState(DEFAULT_TRANSFORM);
  const [ratio, setRatio] = useState("4 / 3");
  const [busy, setBusy] = useState(false);
  const stageRef = useRef(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    if (!photo?.url) return;
    const image = new Image();
    image.onload = () => setRatio(`${image.naturalWidth} / ${image.naturalHeight}`);
    image.src = photo.url;
  }, [photo?.url]);

  useEffect(() => {
    setTransform(DEFAULT_TRANSFORM);
  }, [product?.id]);

  const update = (field, value) => {
    setTransform((previous) => ({ ...previous, [field]: value }));
  };

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  const handlePointerDown = (event) => {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    draggingRef.current = true;
    event.currentTarget.setPointerCapture(event.pointerId);
    moveToPointer(event);
  };

  const moveToPointer = (event) => {
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTransform((previous) => ({
      ...previous,
      x: clamp(((event.clientX - rect.left) / rect.width) * 100, 2, 98),
      y: clamp(((event.clientY - rect.top) / rect.height) * 100, 2, 98),
    }));
  };

  const handlePointerMove = (event) => {
    if (!draggingRef.current) return;
    moveToPointer(event);
  };

  const handlePointerUp = (event) => {
    draggingRef.current = false;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleSave = async () => {
    if (!photo?.file || !product || busy) return;
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append("file", photo.file);
      formData.append("product_id", product.id);
      formData.append("x", transform.x.toFixed(2));
      formData.append("y", transform.y.toFixed(2));
      formData.append("scale", transform.scale.toFixed(3));
      formData.append("rotation", transform.rotation.toFixed(1));
      const blob = await api.compose(formData);
      onSave?.({ url: URL.createObjectURL(blob), blob, product });
    } catch (error) {
      onError?.(error.message || "No fue posible generar la vista previa.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-stone-950/70 p-3 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Vista previa del producto en tu espacio"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose?.();
      }}
    >
      <div className="flex max-h-[94vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-2xl animate-fade-up">
        <div className="flex items-center gap-2 border-b border-stone-200 px-4 py-3">
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-[13px] font-semibold text-stone-800">
              {product?.name || "Vista previa"}
            </h3>
            <p className="text-[10.5px] text-stone-500">
              Arrastra el mueble y ajusta su tamaño o rotación
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-lg p-1.5 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 disabled:opacity-50"
            aria-label="Cerrar editor"
          >
            <X size={17} />
          </button>
        </div>

        <div className="overflow-y-auto px-4 py-3">
          <div
            ref={stageRef}
            className="relative w-full cursor-grab touch-none overflow-hidden rounded-xl bg-stone-900 shadow-inner active:cursor-grabbing"
            style={{ aspectRatio: ratio }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
          >
            <img
              src={photo?.url}
              alt="Espacio compartido por el usuario"
              className="pointer-events-none absolute inset-0 h-full w-full object-contain"
              draggable={false}
            />
            <img
              src={api.productCutoutUrl(product?.id)}
              alt={product?.name || "Producto"}
              onError={(event) => {
                event.currentTarget.src = productImage(product?.image);
              }}
              className="pointer-events-none absolute drop-shadow-[0_12px_16px_rgba(0,0,0,0.45)]"
              style={{
                left: `${transform.x}%`,
                top: `${transform.y}%`,
                width: `${transform.scale * 100}%`,
                transform: `translate(-50%, -50%) rotate(${transform.rotation}deg)`,
                transformOrigin: "center",
              }}
              draggable={false}
            />
          </div>

          <div className="mt-3 space-y-3">
            <label className="block">
              <span className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-stone-500">
                <ZoomIn size={12} /> Tamaño
              </span>
              <input
                type="range"
                min="0.1"
                max="1.2"
                step="0.01"
                value={transform.scale}
                onChange={(event) => update("scale", Number(event.target.value))}
                className="mt-1 w-full accent-jamar"
              />
            </label>
            <label className="block">
              <span className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-wide text-stone-500">
                <RotateCw size={12} /> Rotación
              </span>
              <input
                type="range"
                min="-180"
                max="180"
                step="1"
                value={transform.rotation}
                onChange={(event) => update("rotation", Number(event.target.value))}
                className="mt-1 w-full accent-jamar"
              />
            </label>
          </div>
        </div>

        <div className="border-t border-stone-200 bg-stone-50 px-4 py-3">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setTransform(DEFAULT_TRANSFORM)}
              disabled={busy}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-stone-200 bg-white px-3 py-2 text-[11px] font-semibold text-stone-600 transition hover:bg-stone-100 disabled:opacity-50"
            >
              <RotateCcw size={13} />
              Reiniciar
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="flex-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-[11px] font-semibold text-stone-600 transition hover:bg-stone-100 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={busy}
              className={cn(
                "inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-jamar px-3 py-2",
                "text-[11px] font-semibold text-white transition hover:bg-jamar-deep disabled:opacity-60",
              )}
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              {busy ? "Generando..." : "Guardar en el chat"}
            </button>
          </div>
          <p className="mt-2 flex items-center justify-center gap-1 text-[9.5px] text-stone-400">
            <Move size={10} /> Toca y arrastra sobre la foto para recolocar el mueble
          </p>
        </div>
      </div>
    </div>
  );
}
