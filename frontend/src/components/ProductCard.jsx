import { CreditCard, MapPin, Palette, Package, Ruler, ShoppingBag, Star } from "lucide-react";
import { formatCop, productImage } from "../utils";

/**
 * Tarjeta de producto embebida en la conversación.
 * Prioriza precio, dimensiones y disponibilidad antes de invitar a la acción.
 */
export default function ProductCard({ product, onCredit, onAdd }) {
  const inStock = Number(product.stock) > 0;
  const stockLabel = inStock
    ? `${product.stock} ${product.stock === 1 ? "unidad" : "unidades"}${product.city ? ` en ${product.city}` : " disponibles"}`
    : "Consultar disponibilidad";

  return (
    <article className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-soft animate-fade-up">
      <div className="relative h-28 w-full overflow-hidden bg-stone-100 sm:h-32">
        <img
          src={productImage(product.image)}
          alt={product.name}
          loading="lazy"
          className="h-full w-full object-cover transition duration-500 hover:scale-[1.03]"
          onError={(event) => {
            event.currentTarget.src = "/products/sofa.png";
          }}
        />
        <span
          className={`absolute left-2 top-2 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
            inStock ? "bg-white/95 text-jamar" : "bg-stone-900/80 text-white"
          }`}
        >
          {inStock ? "Disponible" : "Agotado"}
        </span>
        <span className="absolute right-2 top-2 rounded-full bg-stone-900/70 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">
          {product.category}
        </span>
      </div>

      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-semibold leading-snug text-stone-900">{product.name}</h4>
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-gold-light px-1.5 py-0.5 text-[10px] font-semibold text-gold-dark">
            <Star size={10} className="fill-gold text-gold" />
            {Number(product.rating || 0).toFixed(1)}
          </span>
        </div>

        <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-stone-500">
          {product.description || product.material}
        </p>

        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10.5px] text-stone-600">
          <span className="inline-flex items-center gap-1">
            <Ruler size={11} className="text-stone-400" />
            {product.dimensions}
          </span>
          <span className="inline-flex items-center gap-1">
            <Palette size={11} className="text-stone-400" />
            {product.color}
          </span>
          <span className="inline-flex items-center gap-1">
            {product.city ? <MapPin size={11} className="text-stone-400" /> : <Package size={11} className="text-stone-400" />}
            {stockLabel}
          </span>
        </div>

        <div className="mt-3 flex items-end justify-between">
          <p className="text-base font-bold tracking-tight text-jamar">{formatCop(product.price)}</p>
          <span className="text-[10px] text-stone-400">IVA incluido</span>
        </div>

        <div className="mt-2.5 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => onCredit?.(product)}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-jamar px-2 py-2 text-[11px] font-semibold text-white transition hover:bg-jamar-deep focus:outline-none focus-visible:ring-2 focus-visible:ring-jamar/30"
          >
            <CreditCard size={13} />
            Solicitar crédito
          </button>
          <button
            type="button"
            onClick={() => onAdd?.(product)}
            disabled={!inStock}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-stone-200 bg-white px-2 py-2 text-[11px] font-semibold text-stone-700 transition hover:border-jamar/40 hover:bg-jamar-mist hover:text-jamar disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ShoppingBag size={13} />
            Añadir al carrito
          </button>
        </div>
      </div>
    </article>
  );
}
