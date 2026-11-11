import { useState } from "react";
import {
  ArrowRight,
  CreditCard,
  Database,
  MessageCircle,
  ScanLine,
  ShieldCheck,
  Sofa,
  Sparkles,
} from "lucide-react";
import BrandMark from "./components/BrandMark";
import ChatWidget from "./components/ChatWidget";
import { initTelegram } from "./telegram";

const telegram = initTelegram();
const searchParams = new URLSearchParams(window.location.search);
const embedded = searchParams.get("embed") === "1";
const creditFromUrl = searchParams.get("credit") === "1";
const creditPreset = {
  price: Number(searchParams.get("price")) || 2_499_000,
  name: searchParams.get("name") || null,
};

const FEATURES = [
  {
    icon: ScanLine,
    title: "Asesoría de interiores",
    description: "Analiza fotos de tu espacio y recibe muebles compatibles por color, estilo y dimensiones.",
  },
  {
    icon: CreditCard,
    title: "CrediJamar inmediato",
    description: "Simula cuotas semanales y conoce tu pre-aprobación con datos de tu perfil Customer 360.",
  },
  {
    icon: Database,
    title: "Inventario en tiempo real",
    description: "Disponibilidad por ciudad y tienda conectada a Snowflake, sin promesas fuera de stock.",
  },
  {
    icon: MessageCircle,
    title: "Experiencia omnicanal",
    description: "La misma conversación en el widget web, la Mini App y el bot de Telegram.",
  },
];

function FeatureCard({ icon: Icon, title, description }) {
  return (
    <div className="rounded-2xl border border-stone-200/80 bg-white/80 p-4 shadow-soft backdrop-blur-sm transition hover:-translate-y-0.5 hover:border-jamar/25 hover:shadow-card">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-jamar-light text-jamar">
        <Icon size={17} strokeWidth={1.8} />
      </span>
      <h3 className="mt-3 text-[13px] font-semibold text-stone-900">{title}</h3>
      <p className="mt-1 text-[11.5px] leading-relaxed text-stone-500">{description}</p>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div>
      <p className="text-xl font-bold tracking-tight text-jamar">{value}</p>
      <p className="text-[10.5px] uppercase tracking-wide text-stone-400">{label}</p>
    </div>
  );
}

export default function App() {
  const [open, setOpen] = useState(
    () => embedded || searchParams.get("open") === "1" || window.innerWidth >= 1280,
  );
  const [creditRequest, setCreditRequest] = useState(() => (creditFromUrl ? Date.now() : 0));

  const startConversation = () => setOpen(true);
  const simulateCredit = () => {
    setOpen(true);
    setCreditRequest(Date.now());
  };

  if (embedded) {
    return (
      <ChatWidget
        embedded
        telegram={telegram}
        creditRequest={creditRequest}
        creditPreset={creditPreset}
      />
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-cream">
      <div
        className="pointer-events-none absolute -right-48 -top-48 h-[560px] w-[560px] rounded-full bg-jamar/10 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -left-40 bottom-0 h-[420px] w-[420px] rounded-full bg-gold/10 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(11,93,59,0.12) 1px, transparent 0)",
          backgroundSize: "28px 28px",
          maskImage: "linear-gradient(to bottom, black, transparent 70%)",
          WebkitMaskImage: "linear-gradient(to bottom, black, transparent 70%)",
        }}
        aria-hidden="true"
      />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <div className="flex items-center gap-2.5">
          <BrandMark size={40} variant="solid" />
          <div>
            <p className="text-[14px] font-semibold leading-tight text-stone-900">Muebles Jamar</p>
            <p className="text-[9.5px] font-medium uppercase tracking-[0.2em] text-stone-400">
              Asistente de IA
            </p>
          </div>
        </div>

        <nav className="hidden items-center gap-7 text-[11.5px] font-medium text-stone-500 md:flex">
          <a href="#asesoria" className="transition hover:text-jamar">
            Asesoría
          </a>
          <a href="#credito" className="transition hover:text-jamar">
            CrediJamar
          </a>
          <a href="#canales" className="transition hover:text-jamar">
            Canales
          </a>
        </nav>

        <span className="inline-flex items-center gap-1.5 rounded-full border border-jamar/15 bg-white/90 px-3 py-1.5 text-[10px] font-semibold text-jamar shadow-soft">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          Omnicanal en línea
        </span>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-5 pb-20 pt-4 sm:px-8 sm:pt-10">
        <section id="asesoria" className="max-w-3xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold-light/60 px-3 py-1 text-[10.5px] font-semibold uppercase tracking-wide text-gold-dark">
            <Sparkles size={12} />
            Asistencia con IA y analítica Snowflake
          </span>

          <h1 className="mt-5 text-[2.15rem] font-bold leading-[1.1] tracking-tight text-stone-900 sm:text-5xl lg:text-[3.35rem]">
            Diseña, equipa y financia tu hogar{" "}
            <span className="relative inline-block text-jamar">
              con asesoría inteligente.
              <span className="absolute -bottom-1 left-0 h-1.5 w-full rounded-full bg-gold/45" aria-hidden="true" />
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-[14.5px] leading-relaxed text-stone-600">
            Un solo asistente para encontrar el mueble correcto, confirmar disponibilidad en tu
            ciudad y conocer tu cuota CrediJamar. Disponible en la web, en tu celular y dentro de
            Telegram, con el mismo contexto de conversación.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={startConversation}
              className="inline-flex items-center gap-2 rounded-xl bg-jamar px-5 py-3 text-[13px] font-semibold text-white shadow-card transition hover:bg-jamar-deep focus:outline-none focus-visible:ring-4 focus-visible:ring-jamar/25"
            >
              Iniciar conversación
              <ArrowRight size={16} />
            </button>
            <button
              type="button"
              onClick={simulateCredit}
              className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-5 py-3 text-[13px] font-semibold text-stone-700 shadow-soft transition hover:border-jamar/40 hover:text-jamar"
            >
              <CreditCard size={16} />
              Simular mi crédito
            </button>
          </div>

          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2.5 text-[11px] font-medium text-stone-500">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-jamar" />
              Pre-aprobación en tiempo real
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Database size={13} className="text-jamar" />
              Inventario conectado a Snowflake
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Sofa size={13} className="text-jamar" />
              Recomendaciones por espacio
            </span>
          </div>

          <div id="credito" className="mt-12 grid max-w-3xl gap-3 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>

          <div
            id="canales"
            className="mt-12 grid max-w-3xl grid-cols-2 gap-5 border-t border-stone-200/80 pt-6 sm:grid-cols-4"
          >
            <Stat value="6" label="Ciudades" />
            <Stat value="37" label="Tiendas" />
            <Stat value="24/7" label="Asistencia" />
            <Stat value="3" label="Canales integrados" />
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-stone-200/70 bg-white/50">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 py-6 text-[10.5px] text-stone-400 sm:flex-row sm:px-8">
          <div className="flex items-center gap-2">
            <BrandMark size={26} variant="solid" />
            <span>Muebles Jamar · Asistente de IA omnicanal</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Widget web</span>
            <span>Mini App Telegram</span>
            <span>Bot Telegram</span>
            <span>API REST</span>
          </div>
        </div>
      </footer>

      <ChatWidget
        open={open}
        onOpen={() => setOpen(true)}
        onClose={() => setOpen(false)}
        telegram={telegram}
        creditRequest={creditRequest}
        creditPreset={creditPreset}
      />
    </div>
  );
}
