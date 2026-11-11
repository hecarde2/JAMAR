/**
 * Indicador de escritura sutil y elegante para las respuestas del asistente.
 */
export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5" role="status" aria-label="El asistente está escribiendo">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 rounded-full bg-jamar/60 animate-typing-dot"
          style={{ animationDelay: `${index * 160}ms` }}
        />
      ))}
    </div>
  );
}
