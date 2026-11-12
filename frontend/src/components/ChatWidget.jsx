import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  ImagePlus,
  Loader2,
  Minus,
  Plus,
  RotateCcw,
  SendHorizontal,
  ShoppingBag,
  Trash2,
  X,
} from "lucide-react";
import { api } from "../api";
import BrandMark from "./BrandMark";
import CreditSimulator from "./CreditSimulator";
import ImageUploader from "./ImageUploader";
import Launcher from "./Launcher";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import { cn, delay, formatCop, makeId, productImage } from "../utils";
import { hapticFeedback } from "../telegram";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

function readStoredName(telegram) {
  try {
    const stored = localStorage.getItem("jamar_user_name");
    if (stored) return stored;
  } catch {
    // Almacenamiento no disponible; se usa el nombre de Telegram si existe.
  }
  return telegram?.user?.first_name || null;
}

function buildWelcome(telegram, userName) {
  const firstName = (userName || telegram?.user?.first_name || "").split(" ")[0];
  const greeting = firstName ? `Hola, ${firstName}.` : "Hola.";
  const prompt = firstName
    ? "Cuéntame qué estás buscando o comparte una imagen de la habitación."
    : "Para personalizar la asesoría, ¿cómo te llamas? También puedes contarme qué espacio quieres renovar.";
  return [
    {
      id: makeId(),
      role: "assistant",
      ts: Date.now(),
      text:
        `${greeting} Soy el Asistente Jamar. Te ayudo a amueblar tu hogar, consultar ` +
        "inventario por ciudad, analizar una foto de tu espacio y simular tu crédito " +
        `CrediJamar. ${prompt}`,
      suggestions: [
        "Buscar un sofá para mi sala",
        "Simular crédito CrediJamar",
        "Analizar una foto de mi espacio",
      ],
      source: "demo",
    },
  ];
}

function readStoredSession() {
  try {
    return localStorage.getItem("jamar_session_id") || `web-${makeId()}`;
  } catch {
    return `web-${makeId()}`;
  }
}

/**
 * Widget de conversación omnicanal.
 *
 * Se comporta como panel flotante en web, pantalla completa en móvil y como
 * Mini App embebida dentro de Telegram. Mantiene carrito, simulador de crédito
 * y sesión compartida con el bot.
 */
export default function ChatWidget({
  embedded = false,
  open = true,
  onOpen,
  onClose,
  telegram,
  creditRequest = 0,
  creditPreset = null,
}) {
  const [userName, setUserName] = useState(() => readStoredName(telegram));
  const [messages, setMessages] = useState(() => buildWelcome(telegram, readStoredName(telegram)));
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [sessionId, setSessionId] = useState(readStoredSession);
  const [status, setStatus] = useState({ state: "loading", mode: null });
  const [creditOpen, setCreditOpen] = useState(false);
  const [creditSeed, setCreditSeed] = useState({ price: 2_000_000, name: null });
  const [handledCreditRequest, setHandledCreditRequest] = useState(0);
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [roomType, setRoomType] = useState("Sala");

  const scrollRef = useRef(null);
  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const lastFailedRef = useRef(null);

  const cartCount = cart.reduce((total, item) => total + item.qty, 0);
  const cartTotal = cart.reduce((total, item) => total + item.price * item.qty, 0);

  const persistSession = useCallback((value) => {
    if (!value) return;
    setSessionId(value);
    try {
      localStorage.setItem("jamar_session_id", value);
    } catch {
      // Almacenamiento no disponible; la sesión se mantiene en memoria.
    }
  }, []);

  const persistName = useCallback((value) => {
    const cleaned = (value || "").trim();
    if (!cleaned) return;
    setUserName(cleaned);
    try {
      localStorage.setItem("jamar_user_name", cleaned);
    } catch {
      // Almacenamiento no disponible; el nombre se mantiene en memoria.
    }
  }, []);

  const showToast = useCallback((message) => {
    setToast({ id: makeId(), text: message });
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    let active = true;
    api
      .health()
      .then((data) => {
        if (active) setStatus({ state: "online", mode: data });
      })
      .catch(() => {
        if (active) setStatus({ state: "offline", mode: null });
      });
    return () => {
      active = false;
    };
  }, [open]);

  useEffect(() => {
    if (!open || !creditRequest || creditRequest === handledCreditRequest) return;
    setCreditSeed({
      price: Number(creditPreset?.price) || 2_499_000,
      name: creditPreset?.name || null,
    });
    setCreditOpen(true);
    setHandledCreditRequest(creditRequest);
  }, [open, creditRequest, creditPreset, handledCreditRequest]);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, sending, cartOpen]);

  useEffect(() => {
    if (!textareaRef.current) return;
    const element = textareaRef.current;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 108)}px`;
  }, [input]);

  const appendMessage = useCallback((message) => {
    setMessages((previous) => [...previous, { id: makeId(), ts: Date.now(), ...message }]);
  }, []);

  const sendMessage = useCallback(
    async (rawText) => {
      const text = (rawText ?? input).trim();
      if (!text || sending) return;

      hapticFeedback("light");
      appendMessage({ role: "user", text });
      setInput("");
      setSending(true);
      setCartOpen(false);
      lastFailedRef.current = text;
      const startedAt = Date.now();

      try {
        const data = await api.chat({
          message: text.slice(0, 2000),
          session_id: sessionId,
          user_id: telegram?.userId || null,
          name: userName || null,
          channel: telegram?.available ? "telegram" : "web",
        });
        const elapsed = Date.now() - startedAt;
        if (elapsed < 600) await delay(600 - elapsed);

        appendMessage({
          role: "assistant",
          text: data.reply,
          products: data.products || [],
          credit: data.credit || null,
          advisor: data.advisor || null,
          suggestions: data.suggestions || [],
          source: data.source,
          dataSource: data.data_source,
        });
        persistSession(data.session_id);
        if (data.user_name) persistName(data.user_name);
        setStatus((previous) => ({ ...previous, state: "online" }));
        lastFailedRef.current = null;
        hapticFeedback("success");
      } catch (error) {
        appendMessage({
          role: "assistant",
          text: error.message || "No fue posible procesar tu mensaje. Intenta nuevamente.",
          suggestions: ["Ver catálogo", "Hablar con un asesor"],
          isError: true,
        });
        setStatus((previous) => ({ ...previous, state: "offline" }));
        hapticFeedback("error");
      } finally {
        setSending(false);
      }
    },
    [appendMessage, input, persistName, persistSession, sending, sessionId, telegram, userName],
  );

  const handleImage = useCallback(
    async (file) => {
      if (!file || sending) return;
      if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        showToast("Formato no soportado. Usa JPG, PNG o WEBP.");
        return;
      }
      if (file.size > MAX_IMAGE_BYTES) {
        showToast("La imagen supera el límite de 8 MB.");
        return;
      }

      const preview = URL.createObjectURL(file);
      appendMessage({ role: "user", text: "Analiza este espacio", image: preview });
      setSending(true);
      setAnalysisBusy(true);
      setCartOpen(false);

      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("session_id", sessionId);
        formData.append("room_type", roomType);
        if (telegram?.userId) formData.append("user_id", telegram.userId);

        const data = await api.vision(formData);
        appendMessage({
          role: "assistant",
          text: data.reply,
          products: data.products || [],
          analysis: data.analysis,
          suggestions: data.suggestions || [],
          source: data.analysis?.source,
        });
        persistSession(data.session_id);
        setStatus((previous) => ({ ...previous, state: "online" }));
        hapticFeedback("success");
      } catch (error) {
        appendMessage({
          role: "assistant",
          text: error.message || "No fue posible analizar la imagen. Intenta con otra fotografía.",
          suggestions: ["Analizar otra foto", "Ver catálogo"],
          isError: true,
        });
        hapticFeedback("error");
      } finally {
        setSending(false);
        setAnalysisBusy(false);
      }
    },
    [appendMessage, persistSession, roomType, sending, sessionId, showToast, telegram],
  );

  const openCredit = useCallback((product) => {
    const price = Number(product?.price) || 2_000_000;
    setCreditSeed({ price, name: product?.name || null });
    setCreditOpen(true);
    hapticFeedback("light");
  }, []);

  const addToCart = useCallback(
    (product) => {
      hapticFeedback("light");
      setCart((previous) => {
        const existing = previous.find((item) => item.id === product.id);
        if (existing) {
          return previous.map((item) =>
            item.id === product.id ? { ...item, qty: item.qty + 1 } : item,
          );
        }
        return [...previous, { ...product, qty: 1 }];
      });
      showToast(`${product.name} añadido al carrito`);
    },
    [showToast],
  );

  const updateQuantity = useCallback((id, delta) => {
    setCart((previous) =>
      previous
        .map((item) => (item.id === id ? { ...item, qty: item.qty + delta } : item))
        .filter((item) => item.qty > 0),
    );
  }, []);

  const removeFromCart = useCallback((id) => {
    setCart((previous) => previous.filter((item) => item.id !== id));
  }, []);

  const requestCartAdvice = useCallback(() => {
    if (!cart.length) return;
    const detail = cart
      .map((item) => `${item.qty} x ${item.name} (${formatCop(item.price)})`)
      .join(", ");
    const message =
      `Quiero asesoría para completar esta compra: ${detail}. ` +
      `Total ${formatCop(cartTotal)}. ¿Pueden ayudarme con disponibilidad y crédito CrediJamar?`;
    setCartOpen(false);
    sendMessage(message);
  }, [cart, cartTotal, sendMessage]);

  const resetConversation = useCallback(async () => {
    try {
      await api.reset(sessionId, telegram?.userId || null);
    } catch {
      // Si el backend no responde, igual se reinicia la vista local.
    }
    setMessages(buildWelcome(telegram, userName));
    setCart([]);
    setCartOpen(false);
    setCreditOpen(false);
    setInput("");
    persistSession(`web-${makeId()}`);
    showToast("Conversación reiniciada");
  }, [persistSession, sessionId, showToast, telegram, userName]);

  const handleClose = useCallback(() => {
    setCreditOpen(false);
    setCartOpen(false);
    onClose?.();
  }, [onClose]);

  const handleSuggestion = useCallback(
    (suggestion) => {
      if (suggestion === "Reintentar" && lastFailedRef.current) {
        sendMessage(lastFailedRef.current);
        return;
      }
      sendMessage(suggestion);
    },
    [sendMessage],
  );

  const handleComposerSubmit = (event) => {
    event.preventDefault();
    sendMessage();
  };

  const handleComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  if (!embedded && !open) {
    return <Launcher onClick={onOpen} cartCount={cartCount} />;
  }

  return (
    <>
      <div
        className={cn(
          "fixed z-50 flex flex-col overflow-hidden bg-cream",
          embedded
            ? "inset-0"
            : "inset-0 sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[780px] sm:max-h-[calc(100vh-3rem)] sm:w-[430px] sm:rounded-3xl sm:border sm:border-stone-200 sm:shadow-widget",
        )}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(event) => {
          if (event.currentTarget.contains(event.relatedTarget)) return;
          setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          const dropped = event.dataTransfer.files?.[0];
          if (dropped) handleImage(dropped);
        }}
      >
        <header className="relative bg-gradient-to-br from-jamar-deep via-jamar to-jamar-dark px-3.5 pb-3 pt-[max(0.9rem,env(safe-area-inset-top))] text-white sm:px-4">
          <div className="flex items-center gap-2.5">
            <BrandMark size={38} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h2 className="truncate text-[15px] font-semibold leading-tight">Asistente Jamar</h2>
                {status.mode?.snowflake_mode === "demo" && (
                  <span className="rounded-full bg-white/12 px-1.5 py-0.5 text-[8.5px] font-semibold uppercase tracking-wider text-white/80 ring-1 ring-white/15">
                    Demo
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-white/70">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    status.state === "offline"
                      ? "bg-rose-300"
                      : status.state === "loading"
                        ? "bg-gold"
                        : "bg-emerald-300",
                  )}
                />
                <span className="truncate">
                  {status.state === "loading"
                    ? "Conectando con el asistente"
                    : status.state === "offline"
                      ? "Reconectando"
                      : status.mode?.ai_enabled
                        ? "Asesoría con IA · En línea"
                        : "Asesor Jamar · En línea"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => setCartOpen((value) => !value)}
                className="relative rounded-lg p-2 text-white/80 transition hover:bg-white/10 hover:text-white"
                aria-label="Abrir carrito"
              >
                <ShoppingBag size={17} />
                {cartCount > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-gold px-1 text-[9px] font-bold text-white">
                    {cartCount > 9 ? "9+" : cartCount}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={resetConversation}
                className="rounded-lg p-2 text-white/70 transition hover:bg-white/10 hover:text-white"
                aria-label="Reiniciar conversación"
                title="Nueva conversación"
              >
                <RotateCcw size={16} />
              </button>
              {!embedded && (
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-lg p-2 text-white/80 transition hover:bg-white/10 hover:text-white"
                  aria-label="Cerrar asistente"
                >
                  <X size={18} />
                </button>
              )}
            </div>
          </div>
        </header>

        {status.state === "offline" && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-center text-[10px] text-amber-800">
            Sin conexión con el servidor. Puedes escribir y reintentaremos el envío.
          </div>
        )}

        {cartOpen ? (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center gap-2 border-b border-stone-200 bg-white px-3 py-2.5">
              <button
                type="button"
                onClick={() => setCartOpen(false)}
                className="rounded-lg p-1.5 text-stone-500 transition hover:bg-stone-100"
                aria-label="Volver a la conversación"
              >
                <ArrowLeft size={17} />
              </button>
              <div className="flex-1">
                <h3 className="text-[13px] font-semibold text-stone-800">Tu selección</h3>
                <p className="text-[10px] text-stone-500">
                  {cartCount} {cartCount === 1 ? "producto" : "productos"}
                </p>
              </div>
            </div>

            <div className="chat-scroll flex-1 space-y-2.5 overflow-y-auto px-3 py-3">
              {cart.length === 0 ? (
                <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-jamar-light text-jamar">
                    <ShoppingBag size={20} />
                  </span>
                  <p className="text-[12.5px] font-semibold text-stone-700">Tu carrito está vacío</p>
                  <p className="text-[11px] leading-relaxed text-stone-400">
                    Añade productos desde la conversación para recibir asesoría de compra y crédito.
                  </p>
                  <button type="button" onClick={() => setCartOpen(false)} className="chip mt-1">
                    Explorar catálogo
                  </button>
                </div>
              ) : (
                cart.map((item) => (
                  <div key={item.id} className="flex gap-2.5 rounded-xl border border-stone-200 bg-white p-2">
                    <img
                      src={productImage(item.image)}
                      alt={item.name}
                      className="h-16 w-20 shrink-0 rounded-lg bg-stone-100 object-cover"
                      onError={(event) => {
                        event.currentTarget.src = "/products/sofa.png";
                      }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-1">
                        <h4 className="line-clamp-2 text-[11.5px] font-semibold leading-snug text-stone-800">
                          {item.name}
                        </h4>
                        <button
                          type="button"
                          onClick={() => removeFromCart(item.id)}
                          className="rounded p-0.5 text-stone-400 transition hover:text-rose-600"
                          aria-label={`Quitar ${item.name}`}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                      <p className="mt-0.5 text-[11px] font-semibold text-jamar">{formatCop(item.price)}</p>
                      <div className="mt-1.5 flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => updateQuantity(item.id, -1)}
                          className="flex h-5 w-5 items-center justify-center rounded border border-stone-200 text-stone-500 hover:bg-stone-50"
                          aria-label="Disminuir cantidad"
                        >
                          <Minus size={10} />
                        </button>
                        <span className="min-w-4 text-center text-[11px] font-semibold text-stone-700">
                          {item.qty}
                        </span>
                        <button
                          type="button"
                          onClick={() => updateQuantity(item.id, 1)}
                          className="flex h-5 w-5 items-center justify-center rounded border border-stone-200 text-stone-500 hover:bg-stone-50"
                          aria-label="Aumentar cantidad"
                        >
                          <Plus size={10} />
                        </button>
                        <span className="ml-auto text-[10px] font-medium text-stone-400">
                          {formatCop(item.price * item.qty)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="border-t border-stone-200 bg-white px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3">
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-stone-500">Total estimado</span>
                <span className="text-base font-bold text-jamar">{formatCop(cartTotal)}</span>
              </div>
              <button
                type="button"
                onClick={requestCartAdvice}
                disabled={!cart.length}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-jamar px-4 py-2.5 text-[12.5px] font-semibold text-white transition hover:bg-jamar-deep disabled:cursor-not-allowed disabled:opacity-50"
              >
                Solicitar asesoría de compra
              </button>
            </div>
          </div>
        ) : (
          <>
            <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto px-3 py-4 sm:px-4">
              <div className="space-y-4">
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onCredit={openCredit}
                    onAdd={addToCart}
                    onSuggestion={handleSuggestion}
                  />
                ))}

                {messages.length === 1 && (
                  <div className="ml-9 animate-fade-up">
                    <ImageUploader
                      onFile={handleImage}
                      onError={showToast}
                      disabled={sending}
                      roomType={roomType}
                      onRoomTypeChange={setRoomType}
                    />
                  </div>
                )}

                {sending && (
                  <div className="flex items-start gap-2">
                    <BrandMark size={30} variant="solid" className="mt-0.5" />
                    <div className="rounded-2xl rounded-tl-md border border-stone-200/80 bg-white px-3.5 py-3 shadow-soft">
                      <div className="flex items-center gap-2">
                        <TypingIndicator />
                        <span className="text-[10px] text-stone-400">
                          {analysisBusy ? "Analizando tu espacio" : "Asesorando"}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            </div>

            <form
              onSubmit={handleComposerSubmit}
              className="border-t border-stone-200 bg-white/95 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2.5 backdrop-blur"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(event) => {
                  handleImage(event.target.files?.[0]);
                  event.target.value = "";
                }}
              />
              <div className="flex items-end gap-1.5 rounded-2xl border border-stone-200 bg-white p-1.5 shadow-soft transition focus-within:border-jamar/40 focus-within:ring-2 focus-within:ring-jamar/10">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={sending}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-stone-400 transition hover:bg-jamar-mist hover:text-jamar disabled:opacity-50"
                  aria-label="Adjuntar imagen"
                >
                  <ImagePlus size={18} />
                </button>
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleComposerKeyDown}
                  placeholder="Escribe tu mensaje o pide una recomendación"
                  className="max-h-[108px] min-h-[36px] flex-1 resize-none border-0 bg-transparent px-1 py-2 text-[13px] leading-relaxed text-stone-800 outline-none placeholder:text-stone-400"
                  aria-label="Mensaje para el asistente"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || sending}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-jamar text-white transition hover:bg-jamar-deep disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Enviar mensaje"
                >
                  {sending ? <Loader2 size={17} className="animate-spin" /> : <SendHorizontal size={17} />}
                </button>
              </div>
              <p className="mt-1.5 text-center text-[9.5px] text-stone-400">
                Respuestas asistidas por IA · Precios y stock sujetos a disponibilidad
              </p>
            </form>
          </>
        )}

        {dragActive && (
          <div className="pointer-events-none absolute inset-0 z-30 flex flex-col items-center justify-center gap-2 bg-jamar/95 text-white">
            <ImagePlus size={34} strokeWidth={1.5} />
            <p className="text-sm font-semibold">Suelta la imagen para analizarla</p>
            <p className="text-[11px] text-white/70">JPG, PNG o WEBP · máx. 8 MB</p>
          </div>
        )}

        {toast && (
          <div className="absolute bottom-24 left-1/2 z-30 flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full bg-stone-900 px-3.5 py-2 text-[11px] font-medium text-white shadow-lg animate-fade-in">
            <Check size={13} className="text-emerald-300" />
            {toast.text}
          </div>
        )}
      </div>

      <CreditSimulator
        open={creditOpen}
        onClose={() => setCreditOpen(false)}
        initialPrice={creditSeed.price}
        productName={creditSeed.name}
        userId={telegram?.userId || null}
        userName={userName}
        onAdvance={sendMessage}
      />
    </>
  );
}
