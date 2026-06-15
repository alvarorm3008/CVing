import { Clock, History, Trash2 } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";
import { formatDate, jobPreview, DATE_LOCALE_MAP } from "./storage.js";

export default function HistoryPanel({ history, onSelect, onDelete, onClear }) {
  const { t, locale } = useI18n();
  const dateLocale = DATE_LOCALE_MAP[locale] || "es-ES";

  if (!history.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-700/60 bg-slate-900/30 p-6">
        <div className="flex items-center gap-2 text-slate-400">
          <History className="h-5 w-5" />
          <h3 className="font-semibold">{t("history.title")}</h3>
        </div>
        <p className="mt-2 text-sm text-slate-500">{t("history.empty")}</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6 backdrop-blur-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-400" />
          <h3 className="font-semibold text-white">
            {t("history.title")} ({history.length})
          </h3>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="text-sm text-slate-400 transition hover:text-rose-400"
        >
          {t("history.clear")}
        </button>
      </div>

      <ul className="space-y-2">
        {history.map((entry) => (
          <li
            key={entry.id}
            className="group flex items-stretch overflow-hidden rounded-xl border border-slate-700/50 bg-slate-800/40 transition hover:border-indigo-500/40"
          >
            <button
              type="button"
              onClick={() => onSelect(entry)}
              className="flex flex-1 flex-col gap-1 p-4 text-left transition hover:bg-slate-800/60"
            >
              <span className="font-medium text-slate-200">
                {entry.ats_match?.target_role || t("history.adaptation")}
                <span className="ml-2 text-xs text-indigo-400">
                  {entry.adaptation_mode === "ats-perfect" ? t("history.ats") : t("history.honest")}
                  {entry.full_application ? ` · ${t("history.full")}` : ""}
                </span>
              </span>
              <span className="flex items-center gap-2 text-xs text-slate-500">
                <Clock className="h-3 w-3" />
                {formatDate(entry.createdAt, dateLocale)} · ATS{" "}
                {entry.ats_match?.honest_score ?? entry.ats_match?.score ?? 0}%
                {entry.ats_match?.potential_score
                  ? ` → ${entry.ats_match.potential_score}%`
                  : ""}
              </span>
              <span className="line-clamp-1 text-xs text-slate-600">
                {jobPreview(entry.jobDescription)}
              </span>
            </button>
            <button
              type="button"
              onClick={() => onDelete(entry.id)}
              className="flex items-center px-4 text-slate-500 transition hover:bg-rose-500/10 hover:text-rose-400"
              aria-label={t("history.delete")}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
