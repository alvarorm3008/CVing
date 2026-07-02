import { motion } from "framer-motion";
import { CheckCircle2, Download, Mail, Package } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";
import { coverLetterDisplayText } from "./coverLetterUtils.js";

export default function ApplicationReadyBanner({
  companyName,
  jobTitle,
  onDownloadCv,
  onDownloadLetter,
  onDownloadPack,
  downloading,
}) {
  const { t } = useI18n();

  const subtitle =
    companyName && jobTitle
      ? t("pack.subtitle").replace("{jobTitle}", jobTitle).replace("{companyName}", companyName)
      : t("pack.subtitleGeneric");

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-800">
            <CheckCircle2 className="h-6 w-6" />
            <h3 className="text-lg font-bold text-neutral-900">{t("pack.title")}</h3>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-neutral-800">{subtitle}</p>
          <ul className="mt-3 space-y-1 text-sm text-neutral-700">
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-700" />
              {t("pack.itemCv")}
            </li>
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-700" />
              {t("pack.itemResearch")}
            </li>
            <li className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-emerald-700" />
              {t("pack.itemLetter")}
            </li>
          </ul>
        </div>
        <div className="flex flex-wrap gap-2">
          {onDownloadPack && (
            <button
              type="button"
              onClick={onDownloadPack}
              disabled={downloading}
              className="btn-primary bg-emerald-700 hover:bg-emerald-800"
            >
              <Package className="h-4 w-4" />
              {downloading ? t("pack.downloading") : t("pack.downloadPack")}
            </button>
          )}
          <button
            type="button"
            onClick={onDownloadCv}
            disabled={downloading}
            className="btn-secondary"
          >
            <Download className="h-4 w-4" />
            {t("pack.downloadCv")}
          </button>
          <button type="button" onClick={onDownloadLetter} disabled={downloading} className="btn-secondary">
            <Mail className="h-4 w-4" />
            {t("pack.downloadLetter")}
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
