import { Check, FileText, Globe, Loader2, Mail } from "lucide-react";
import clsx from "clsx";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function ApplicationProgress({ currentStep, active, indeterminate = false }) {
  const { t } = useI18n();

  const STEPS = [
    { id: 1, label: t("fullApp.stepAdapt"), icon: FileText },
    { id: 2, label: t("fullApp.stepResearch"), icon: Globe },
    { id: 3, label: t("fullApp.stepLetter"), icon: Mail },
  ];

  if (!active) return null;

  if (indeterminate) {
    return (
      <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-neutral-700" />
          <p className="text-sm font-semibold text-neutral-900">{t("fullApp.progressTitle")}</p>
        </div>
        <p className="mb-4 text-sm text-neutral-700">{t("progress.indeterminate")}</p>
        <ol className="space-y-2">
          {STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <li key={step.id} className="flex items-center gap-3 rounded-xl bg-neutral-50 px-4 py-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-200 text-neutral-600">
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <span className="text-sm text-neutral-700">{step.label}</span>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <p className="mb-4 text-sm font-semibold text-neutral-900">{t("fullApp.progressTitle")}</p>
      <ol className="space-y-3">
        {STEPS.map((step) => {
          const Icon = step.icon;
          const done = currentStep > step.id;
          const running = currentStep === step.id;

          return (
            <li
              key={step.id}
              className={clsx(
                "flex items-center gap-3 rounded-xl px-4 py-3 transition",
                done && "bg-emerald-50",
                running && "bg-neutral-100 ring-1 ring-neutral-300",
                !done && !running && "opacity-50",
              )}
            >
              <span
                className={clsx(
                  "flex h-8 w-8 items-center justify-center rounded-full",
                  done && "bg-emerald-200 text-emerald-900",
                  running && "bg-neutral-800 text-white",
                  !done && !running && "bg-neutral-200 text-neutral-600",
                )}
              >
                {done ? (
                  <Check className="h-4 w-4" />
                ) : running ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </span>
              <span
                className={clsx(
                  "text-sm font-medium",
                  done && "text-emerald-900",
                  running && "text-neutral-900",
                  !done && !running && "text-neutral-600",
                )}
              >
                {step.label}
                {running && "…"}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
