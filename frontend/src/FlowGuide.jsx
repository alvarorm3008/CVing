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
    <nav aria-label={t("flow.title")} className="border-y border-neutral-300/70 py-4">
      <ol className="grid grid-cols-3 gap-3 sm:gap-6">
        {steps.map((step) => {
          const done = currentStep > step.id;
          const active = currentStep === step.id;
          return (
            <li
              key={step.id}
              aria-current={active ? "step" : undefined}
              className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-3"
            >
              <span
                className={clsx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-xs transition-colors duration-300",
                  done && "bg-emerald-700 text-white",
                  active && !done && "bg-accent-600 text-white",
                  !done && !active && "border border-neutral-300 text-neutral-500",
                )}
              >
                {done ? <CheckCircle2 className="h-4 w-4" /> : `0${step.id}`}
              </span>
              <span
                className={clsx(
                  "text-sm leading-snug",
                  active ? "font-semibold text-neutral-950" : done ? "text-neutral-700" : "text-neutral-500",
                )}
              >
                {step.label}
              </span>
              <span
                aria-hidden="true"
                className={clsx(
                  "hidden h-px flex-1 sm:block",
                  done ? "bg-emerald-700/40" : "bg-neutral-300",
                  step.id === steps.length && "sm:hidden",
                )}
              />
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
