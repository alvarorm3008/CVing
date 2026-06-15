import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  GraduationCap,
  Send,
  Target,
  TrendingUp,
} from "lucide-react";
import clsx from "clsx";
import { useI18n } from "./i18n/I18nContext.jsx";

function ScoreRing({ score, label, variant }) {
  const color =
    score >= 80 ? "text-emerald-400" : score >= 60 ? "text-amber-400" : "text-rose-400";
  const ring =
    score >= 80 ? "stroke-emerald-500" : score >= 60 ? "stroke-amber-500" : "stroke-rose-500";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative h-20 w-20">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.5" fill="none" className="stroke-slate-700" strokeWidth="3" />
          <circle
            cx="18"
            cy="18"
            r="15.5"
            fill="none"
            className={ring}
            strokeWidth="3"
            strokeDasharray={`${score} 100`}
            strokeLinecap="round"
          />
        </svg>
        <span className={clsx("absolute inset-0 flex items-center justify-center text-lg font-bold", color)}>
          {score}%
        </span>
      </div>
      <span className="text-center text-xs text-slate-400">{label}</span>
      {variant === "potential" && (
        <TrendingUp className="h-3.5 w-3.5 text-indigo-400" />
      )}
    </div>
  );
}

function PriorityTag({ priority }) {
  const labels = { high: "Alta", medium: "Media", low: "Baja" };
  const colors = {
    high: "bg-rose-500/20 text-rose-300",
    medium: "bg-amber-500/20 text-amber-300",
    low: "bg-slate-500/20 text-slate-300",
  };
  return (
    <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", colors[priority])}>
      {labels[priority] || priority}
    </span>
  );
}

export default function ATSMatchPanel({ atsMatch, onReboost, reboosting }) {
  const { t } = useI18n();

  const APPLY_CONFIG = {
    apply_now: {
      text: t("ats.applyNow"),
      icon: CheckCircle2,
      className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    },
    apply_after_learning: {
      text: t("ats.applyAfter"),
      icon: GraduationCap,
      className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    },
    not_recommended: {
      text: t("ats.notRecommended"),
      icon: AlertTriangle,
      className: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    },
    send_cv: {
      text: t("ats.sendCv"),
      icon: Send,
      className: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
    },
  };

  const MODE_CONFIG = {
    honest: {
      title: t("ats.honestTitle"),
      honestLabel: t("ats.honestLabel"),
      potentialLabel: t("ats.potentialLabel"),
      badge: t("ats.consultant"),
      showLearning: true,
    },
    "ats-perfect": {
      title: t("ats.atsTitle"),
      honestLabel: t("ats.atsScore"),
      potentialLabel: null,
      badge: t("ats.sendMode"),
      showLearning: false,
    },
  };

  if (!atsMatch) return null;

  const mode = atsMatch.adaptation_mode || "honest";
  const config = MODE_CONFIG[mode] || MODE_CONFIG.honest;
  const honestScore = atsMatch.honest_score ?? atsMatch.score ?? 0;
  const potentialScore = atsMatch.potential_score ?? honestScore;
  const passesAts = honestScore >= 80;
  const applyConfig = APPLY_CONFIG[atsMatch.apply_recommendation] || APPLY_CONFIG.apply_after_learning;
  const ApplyIcon = applyConfig.icon;

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-6 backdrop-blur-sm"
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-300">
          {config.badge}
        </span>
        {atsMatch.target_role && (
          <span className="flex items-center gap-1 text-sm text-slate-400">
            <Target className="h-3.5 w-3.5" />
            {atsMatch.target_role}
          </span>
        )}
      </div>

      {atsMatch.apply_recommendation && (
        <div className={clsx("mb-5 rounded-xl border p-4", applyConfig.className)}>
          <div className="flex items-center gap-2 font-semibold">
            <ApplyIcon className="h-5 w-5" />
            {applyConfig.text}
          </div>
          {atsMatch.apply_recommendation_reason && (
            <p className="mt-2 text-sm opacity-90">{atsMatch.apply_recommendation_reason}</p>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h3 className="text-xl font-bold text-white">{config.title}</h3>
          {atsMatch.optimization_notes && (
            <p className="mt-2 max-w-xl text-sm text-slate-400">{atsMatch.optimization_notes}</p>
          )}
        </div>
        <div className="flex gap-6">
          <ScoreRing score={honestScore} label={config.honestLabel} variant="honest" />
          {config.potentialLabel && (
            <ScoreRing score={potentialScore} label={config.potentialLabel} variant="potential" />
          )}
        </div>
      </div>

      {mode === "ats-perfect" && !passesAts && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
          <p className="text-sm text-amber-200">
            Score por debajo de 80%. Puedes reforzar con una segunda pasada ATS.
          </p>
          {onReboost && (
            <button
              type="button"
              onClick={onReboost}
              disabled={reboosting}
              className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-amber-400 disabled:opacity-50"
            >
              {reboosting ? t("actions.reboosting") : t("actions.reboost")}
            </button>
          )}
        </div>
      )}

      {atsMatch.skills_you_have?.length > 0 && (
        <div className="mt-6">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            {mode === "ats-perfect" ? "Keywords alineadas" : "Lo que ya demuestras"}
          </h4>
          <div className="space-y-2">
            {atsMatch.skills_you_have.map((item, index) => (
              <div
                key={`${item.requirement}-${index}`}
                className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <strong className="text-slate-200">{item.requirement}</strong>
                  <span
                    className={clsx(
                      "rounded-full px-2 py-0.5 text-xs",
                      item.match_level === "covered"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : "bg-amber-500/20 text-amber-300",
                    )}
                  >
                    {item.match_level === "covered" ? "Cubierto" : "Parcial"}
                  </span>
                </div>
                {item.evidence && <p className="mt-1 text-sm text-slate-400">{item.evidence}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {config.showLearning && atsMatch.skills_to_learn?.length > 0 && (
        <div className="mt-6">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Qué aprender antes de presentarte
          </h4>
          <div className="space-y-3">
            {atsMatch.skills_to_learn.map((item) => (
              <div key={item.skill} className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <strong className="text-indigo-200">{item.skill}</strong>
                  <PriorityTag priority={item.priority} />
                </div>
                {item.why_needed && <p className="mt-2 text-sm text-slate-300">{item.why_needed}</p>}
                {item.how_to_learn && (
                  <p className="mt-1 text-sm text-slate-400">
                    <span className="font-medium text-slate-300">Cómo: </span>
                    {item.how_to_learn}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {mode === "ats-perfect" && (atsMatch.cv_improvements?.length > 0 || atsMatch.missing_keywords?.length > 0) && (
        <div className="mt-6">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            {t("ats.improveTitle")}
          </h4>
          {atsMatch.cv_improvements?.length > 0 && (
            <ul className="mb-4 space-y-2">
              {atsMatch.cv_improvements.map((item, index) => (
                <li
                  key={`improve-${index}`}
                  className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm text-amber-100"
                >
                  {item}
                </li>
              ))}
            </ul>
          )}
          {atsMatch.missing_keywords?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {atsMatch.missing_keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-300"
                >
                  {keyword}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {mode === "honest" && atsMatch.missing_keywords?.length > 0 && (
        <div className="mt-6">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Requisitos que aún no cubres
          </h4>
          <div className="flex flex-wrap gap-2">
            {atsMatch.missing_keywords.map((keyword) => (
              <span
                key={keyword}
                className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-300"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.section>
  );
}
