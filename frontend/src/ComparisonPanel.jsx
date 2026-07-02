import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { useI18n } from "./i18n/I18nContext.jsx";

function countChanges(original, adapted) {
  let changes = 0;
  if ((original?.summary || "") !== (adapted?.summary || "")) changes += 1;
  if (JSON.stringify(original?.skills || []) !== JSON.stringify(adapted?.skills || [])) {
    changes += 1;
  }
  const origBullets = (original?.experience || []).flatMap((e) => e.bullets || []);
  const newBullets = (adapted?.experience || []).flatMap((e) => e.bullets || []);
  if (JSON.stringify(origBullets) !== JSON.stringify(newBullets)) changes += 1;
  return changes;
}

function MiniCV({ cv, label, accent }) {
  if (!cv) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${accent}`} />
        <span className="text-xs font-semibold uppercase tracking-wider text-neutral-600">{label}</span>
      </div>
      <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm">
        <h4 className="font-bold text-neutral-900">{cv.contact?.full_name || "CV"}</h4>
        {cv.summary && <p className="mt-2 line-clamp-3 text-neutral-700">{cv.summary}</p>}
        {cv.skills?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {cv.skills.slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="rounded-full border border-neutral-200 bg-white px-2 py-0.5 text-xs text-neutral-800"
              >
                {skill}
              </span>
            ))}
            {cv.skills.length > 8 && (
              <span className="text-xs text-neutral-500">+{cv.skills.length - 8}</span>
            )}
          </div>
        )}
        {cv.experience?.[0] && (
          <div className="mt-3 border-t border-neutral-200 pt-3">
            <p className="font-medium text-neutral-900">{cv.experience[0].role}</p>
            {cv.experience[0].bullets?.[0] && (
              <p className="mt-1 line-clamp-2 text-xs text-neutral-600">
                {cv.experience[0].bullets[0]}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ComparisonPanel({ originalCv, adaptedCv, boosted }) {
  const { t } = useI18n();
  if (!originalCv || !adaptedCv) return null;

  const changes = countChanges(originalCv, adaptedCv);

  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="panel">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-neutral-700" />
          <h3 className="font-semibold text-neutral-900">{t("comparison.title")}</h3>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-neutral-100 px-2.5 py-1 font-medium text-neutral-800">
            {t("comparison.changes").replace("{count}", String(changes))}
          </span>
          {boosted && (
            <span className="rounded-full bg-emerald-100 px-2.5 py-1 font-medium text-emerald-900">
              {t("comparison.boosted")}
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
        <MiniCV cv={originalCv} label={t("comparison.original")} accent="bg-neutral-400" />
        <ArrowRight className="mx-auto hidden h-6 w-6 text-neutral-500 md:block" />
        <MiniCV cv={adaptedCv} label={t("comparison.adapted")} accent="bg-neutral-900" />
      </div>
    </motion.section>
  );
}
