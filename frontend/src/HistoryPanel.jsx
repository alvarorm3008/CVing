import { Clock, History, Trash2 } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";
import {
  formatDate,
  jobPreview,
  DATE_LOCALE_MAP,
  HISTORY_STATUSES,
} from "./storage.js";

const STATUS_LABEL_KEYS = {
  prepared: "history.statusPrepared",
  sent: "history.statusSent",
  interview: "history.statusInterview",
  rejected: "history.statusRejected",
};

export default function HistoryPanel({ history, onSelect, onDelete, onClear, onStatusChange }) {
  const { t, locale } = useI18n();
  const dateLocale = DATE_LOCALE_MAP[locale] || "es-ES";

  if (!history.length) {
    return (
      <section className="rounded-2xl border border-dashed border-neutral-300 bg-white p-6">
        <div className="flex items-center gap-2 text-neutral-700">
          <History className="h-5 w-5" />
          <h3 className="font-semibold text-neutral-900">{t("history.title")}</h3>
        </div>
        <p className="mt-2 text-sm text-neutral-600">{t("history.empty")}</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-neutral-700" />
          <h3 className="font-semibold text-neutral-900">
            {t("history.title")} ({history.length})
          </h3>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="text-sm font-medium text-neutral-600 transition hover:text-rose-700"
        >
          {t("history.clear")}
        </button>
      </div>

      <ul className="space-y-2">
        {history.map((entry) => (
          <li
            key={entry.id}
            className="group flex items-stretch overflow-hidden rounded-xl border border-neutral-200 bg-neutral-50 transition hover:border-neutral-400"
          >
            <button
              type="button"
              onClick={() => onSelect(entry)}
              className="flex flex-1 flex-col gap-1 p-4 text-left transition hover:bg-white"
            >
              <span className="font-medium text-neutral-900">
                {entry.ats_match?.target_role || t("history.adaptation")}
                <span className="ml-2 text-xs font-normal text-neutral-600">
                  {entry.adaptation_mode === "honest"
                    ? t("history.honest")
                    : entry.adaptation_mode === "ats-perfect"
                      ? t("history.ats")
                      : entry.adaptation_mode || t("history.ats")}
                  {entry.full_application ? ` · ${t("history.full")}` : ""}
                </span>
              </span>
              <span className="flex items-center gap-2 text-xs text-neutral-600">
                <Clock className="h-3 w-3" />
                {formatDate(entry.createdAt, dateLocale)} · ATS{" "}
                {entry.ats_match?.honest_score ?? entry.ats_match?.score ?? 0}%
              </span>
              <span className="line-clamp-1 text-xs text-neutral-500">
                {jobPreview(entry.jobDescription)}
              </span>
            </button>
            <select
              aria-label={t("history.statusPrepared")}
              value={entry.status || "prepared"}
              onChange={(e) => onStatusChange(entry.id, e.target.value)}
              onClick={(e) => e.stopPropagation()}
              className="self-center border-0 bg-transparent px-2 text-xs font-medium text-neutral-600 focus:ring-0"
            >
              {HISTORY_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {t(STATUS_LABEL_KEYS[status])}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => onDelete(entry.id)}
              className="flex items-center px-4 text-neutral-500 transition hover:bg-rose-50 hover:text-rose-700"
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
