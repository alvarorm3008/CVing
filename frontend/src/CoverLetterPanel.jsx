import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Download, Mail, Pencil } from "lucide-react";
import clsx from "clsx";
import { coverLetterDisplayText } from "./coverLetterUtils.js";

export default function CoverLetterPanel({ coverLetter, onChange, loading }) {
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);

  if (loading) {
    return (
      <section className="panel">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
          <p className="text-neutral-800">Redactando carta personalizada…</p>
        </div>
      </section>
    );
  }

  if (!coverLetter) return null;

  const text = coverLetterDisplayText(coverLetter);

  if (!text) {
    return (
      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">
        No se pudo mostrar la carta (respuesta vacía). Prueba de nuevo sin modo rápido o regenera la candidatura.
      </section>
    );
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "carta-presentacion.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleTextChange = (value) => {
    onChange({ ...coverLetter, full_text: value });
  };

  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="panel">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-neutral-700" />
          <h3 className="text-xl font-bold text-neutral-900">Carta de presentación</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className={clsx(
              "btn-secondary px-3 py-2",
              editing && "bg-neutral-100 ring-1 ring-neutral-300",
            )}
          >
            <Pencil className="h-4 w-4" />
            {editing ? "Vista previa" : "Editar"}
          </button>
          <button type="button" onClick={handleCopy} className="btn-secondary px-3 py-2">
            {copied ? <Check className="h-4 w-4 text-emerald-700" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copiado" : "Copiar"}
          </button>
          <button type="button" onClick={handleDownload} className="btn-primary px-3 py-2">
            <Download className="h-4 w-4" />
            Descargar .txt
          </button>
        </div>
      </div>

      {coverLetter.subject_line && (
        <p className="mb-3 text-sm text-neutral-700">
          <span className="font-semibold text-neutral-900">Asunto: </span>
          {coverLetter.subject_line}
        </p>
      )}

      {coverLetter.personalization_hooks?.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {coverLetter.personalization_hooks.map((hook) => (
            <span
              key={hook}
              className="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-medium text-neutral-800"
            >
              {hook}
            </span>
          ))}
        </div>
      )}

      {editing ? (
        <textarea
          rows={16}
          value={text}
          onChange={(e) => handleTextChange(e.target.value)}
          className="input-field font-serif leading-relaxed"
        />
      ) : (
        <article className="rounded-xl border border-neutral-200 bg-neutral-50 p-8 font-serif text-base leading-relaxed text-neutral-900">
          {text.split("\n\n").map((paragraph, index) => (
            <p key={index} className={index > 0 ? "mt-4" : ""}>
              {paragraph}
            </p>
          ))}
        </article>
      )}
    </motion.section>
  );
}
