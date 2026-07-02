import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { useI18n } from "./i18n/I18nContext.jsx";
import { computeChanges } from "./changesUtils.js";

export default function ChangesPanel({ originalCv, adaptedCv, atsMatch }) {
  const { t } = useI18n();
  const { addedKeywords, newSkills, bulletChanges, missingKeywords } = computeChanges(
    originalCv,
    adaptedCv,
    atsMatch,
  );

  const hasContent =
    addedKeywords.length > 0 || newSkills.length > 0 || bulletChanges.length > 0 || missingKeywords.length > 0;

  if (!hasContent) return null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-neutral-700" />
        <h3 className="font-bold text-neutral-900">{t("changes.title")}</h3>
      </div>

      {addedKeywords.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-600">
            {t("changes.keywordsAdded")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {addedKeywords.map((kw) => (
              <span key={kw} className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-900">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {newSkills.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-600">
            {t("changes.skillsAdded")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {newSkills.map((skill) => (
              <span key={skill} className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-800">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {bulletChanges.length > 0 && (
        <div className="mb-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">
            {t("changes.bulletsRewritten")}
          </p>
          {bulletChanges.slice(0, 5).map((change, i) => (
            <div key={`${change.role}-${i}`} className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm">
              <p className="text-xs font-medium text-neutral-500">
                {change.role}
                {change.company ? ` · ${change.company}` : ""}
              </p>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-start">
                <p className="flex-1 text-neutral-500 line-through">{change.before}</p>
                <ArrowRight className="hidden h-4 w-4 shrink-0 text-neutral-400 sm:mt-1 sm:block" />
                <p className="flex-1 text-neutral-800">{change.after}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {missingKeywords.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-semibold text-amber-950">{t("changes.stillMissing")}</p>
          <p className="mt-1 text-sm text-amber-900">{missingKeywords.slice(0, 6).join(", ")}</p>
          <p className="mt-2 text-xs text-amber-800">{t("changes.disclaimer")}</p>
        </div>
      )}
    </motion.section>
  );
}
