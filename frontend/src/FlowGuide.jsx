import clsx from "clsx";
import { CheckCircle2 } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function FlowGuide({ currentStep = 1 }) {
  const { t } = useI18n();

  const steps = [
    { id: 1, label: t("flow.stepCheck") },
    { id: 2, label: t("flow.stepAdapt") },
    { id: 3, label: t("flow.stepDownload") },
  ];

  return (
    <nav aria-label={t("flow.title")} className="rounded-2xl border border-neutral-200 bg-white px-4 py-4 shadow-sm">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">{t("flow.title")}</p>
      <ol className="flex flex-wrap items-center gap-2 sm:gap-4">
        {steps.map((step, index) => {
          const done = currentStep > step.id;
          const active = currentStep === step.id;
          return (
            <li key={step.id} className="flex items-center gap-2">
              {index > 0 && <span className="hidden text-neutral-300 sm:inline">→</span>}
              <span
                className={clsx(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                  done && "bg-emerald-100 text-emerald-900",
                  active && !done && "bg-neutral-900 text-white",
                  !done && !active && "bg-neutral-100 text-neutral-600",
                )}
              >
                {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span>{step.id}</span>}
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
