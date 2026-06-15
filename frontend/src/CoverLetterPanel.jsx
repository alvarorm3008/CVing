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
      <section className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
          <p className="text-slate-300">Redactando carta personalizada…</p>
        </div>
      </section>
    );
  }

  if (!coverLetter) return null;

  const text = coverLetterDisplayText(coverLetter);

  if (!text) {
    return (
      <section className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 text-amber-200">
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
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-slate-900/90 to-violet-950/20 p-6 backdrop-blur-sm"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-violet-400" />
          <h3 className="text-xl font-bold text-white">Carta de presentación</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
              editing
                ? "bg-violet-500/20 text-violet-300"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700",
            )}
          >
            <Pencil className="h-4 w-4" />
            {editing ? "Vista previa" : "Editar"}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copiado" : "Copiar"}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500"
          >
            <Download className="h-4 w-4" />
            Descargar .txt
          </button>
        </div>
      </div>

      {coverLetter.subject_line && (
        <p className="mb-3 text-sm text-slate-400">
          <span className="font-medium text-slate-300">Asunto: </span>
          {coverLetter.subject_line}
        </p>
      )}

      {coverLetter.personalization_hooks?.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {coverLetter.personalization_hooks.map((hook) => (
            <span
              key={hook}
              className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-xs text-violet-300"
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
          className="w-full rounded-xl border border-slate-600 bg-slate-800/80 px-4 py-3 font-serif text-slate-100 leading-relaxed focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
        />
      ) : (
        <article className="rounded-xl border border-slate-700/50 bg-white p-8 font-serif text-slate-800 leading-relaxed shadow-lg">
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
