import { Loader2, ScanSearch } from "lucide-react";
import clsx from "clsx";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function PreflightPanel({ data, loading, offerLanguage, onAdaptClick }) {
  const { t } = useI18n();

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-600">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("preflight.loading")}
      </div>
    );
  }

  if (!data) return null;

  const total = data.total_keywords ?? 0;
  const matched = data.matched_keywords?.length ?? 0;
  const missing = data.missing_keywords?.length ?? 0;
  const score = data.honest_score ?? data.score ?? 0;
  const missingPreview = (data.missing_keywords ?? []).slice(0, 4).join(", ");

  return (
    <section className="rounded-2xl border border-neutral-200 bg-gradient-to-br from-white to-neutral-50 px-5 py-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-neutral-100">
            <ScanSearch className="h-4 w-4 text-neutral-700" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-neutral-900">{t("preflight.title")}</h3>
            <p className="mt-1 text-sm text-neutral-600">
              {offerLanguage?.name
                ? t("preflight.lang").replace("{language}", offerLanguage.name)
                : null}
              {total > 0
                ? ` · ${t("preflight.stats")
                    .replace("{total}", String(total))
                    .replace("{matched}", String(matched))
                    .replace("{missing}", String(missing))}`
                : ` · ${t("preflight.noTech")}`}
            </p>
            {total > 0 && (
              <p className="mt-1 text-xs text-neutral-500">
                {t("preflight.score").replace("{score}", String(score))}
              </p>
            )}
          </div>
        </div>
        {missing > 0 && onAdaptClick && (
          <button type="button" onClick={onAdaptClick} className="btn-primary px-3 py-1.5 text-xs">
            {t("preflight.cta").replace("{keywords}", missingPreview || "…")}
          </button>
        )}
      </div>
      {missing > 0 && (
        <p className={clsx("mt-2 text-xs text-amber-800")}>{t("preflight.disclaimer")}</p>
      )}
    </section>
  );
}
