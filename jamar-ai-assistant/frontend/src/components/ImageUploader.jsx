import { useRef, useState } from "react";
import { ImagePlus, ScanLine } from "lucide-react";
import { cn } from "../utils";

const MAX_BYTES = 8 * 1024 * 1024;
const ALLOWED = ["image/jpeg", "image/png", "image/webp"];

/**
 * Zona de carga de imágenes con soporte para arrastrar y soltar.
 * La imagen se envía al endpoint /api/vision para el análisis del espacio.
 */
export default function ImageUploader({
  onFile,
  onError,
  disabled = false,
  roomType = "Sala",
  onRoomTypeChange,
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const validateAndSend = (file) => {
    if (!file) return;
    if (!ALLOWED.includes(file.type)) {
      onError?.("Formato no soportado. Usa una imagen JPG, PNG o WEBP.");
      return;
    }
    if (file.size > MAX_BYTES) {
      onError?.("La imagen supera el límite de 8 MB.");
      return;
    }
    onFile?.(file);
  };

  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-2.5 shadow-soft">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(event) => {
          validateAndSend(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) validateAndSend(event.dataTransfer.files?.[0]);
        }}
        className={cn(
          "flex w-full flex-col items-center gap-1.5 rounded-xl border border-dashed px-3 py-4 text-center transition",
          dragging
            ? "border-jamar bg-jamar-mist"
            : "border-stone-300 bg-stone-50/60 hover:border-jamar/50 hover:bg-jamar-mist/60",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-jamar-light text-jamar">
          {dragging ? <ScanLine size={17} /> : <ImagePlus size={17} />}
        </span>
        <span className="text-[12px] font-semibold text-stone-700">
          Arrastra una foto de tu espacio
        </span>
        <span className="text-[10.5px] text-stone-400">
          o selecciona un archivo · JPG, PNG o WEBP · máx. 8 MB
        </span>
      </button>

      {onRoomTypeChange && (
        <div className="mt-2 flex items-center justify-between gap-2 px-1">
          <label htmlFor="room-type" className="text-[10.5px] font-medium text-stone-500">
            Espacio a analizar
          </label>
          <select
            id="room-type"
            value={roomType}
            onChange={(event) => onRoomTypeChange(event.target.value)}
            className="rounded-lg border border-stone-200 bg-white px-2 py-1 text-[11px] font-medium text-stone-700 outline-none focus:border-jamar"
          >
            <option value="Sala">Sala</option>
            <option value="Comedor">Comedor</option>
            <option value="Alcoba">Alcoba</option>
            <option value="Oficina">Oficina</option>
            <option value="Almacenamiento">Almacenamiento</option>
          </select>
        </div>
      )}
    </div>
  );
}
