import { motion } from "framer-motion";
import { CheckCircle2, Download, Mail, Package } from "lucide-react";

import { coverLetterDisplayText } from "./coverLetterUtils.js";

export default function ApplicationReadyBanner({
  companyName,
  jobTitle,
  onDownloadCv,
  onDownloadLetter,
  downloading,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-indigo-500/10 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-300">
            <CheckCircle2 className="h-6 w-6" />
            <h3 className="text-lg font-bold text-white">Candidatura lista</h3>
          </div>
          <p className="mt-2 text-sm text-slate-300">
            {companyName && jobTitle
              ? `Todo preparado para aplicar a ${jobTitle} en ${companyName}.`
              : "CV adaptado, investigación de empresa y carta de presentación generados."}
          </p>
          <ul className="mt-3 space-y-1 text-xs text-slate-400">
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-400" />
              CV adaptado + PDF
            </li>
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-400" />
              Investigación de empresa y salario
            </li>
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-400" />
              Carta de presentación personalizada
            </li>
          </ul>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onDownloadCv}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Descargar CV
          </button>
          <button
            type="button"
            onClick={onDownloadLetter}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-50"
          >
            <Mail className="h-4 w-4" />
            Descargar carta
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function downloadLetterText(coverLetter) {
  const text = coverLetterDisplayText(coverLetter);
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "carta-presentacion.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export { downloadLetterText };
