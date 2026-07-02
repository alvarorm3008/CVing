import { motion } from "framer-motion";
import {
  Building2,
  ExternalLink,
  MapPin,
  Route,
  Star,
  ThumbsDown,
  ThumbsUp,
  Wallet,
} from "lucide-react";
import clsx from "clsx";

const CONFIDENCE_LABELS = {
  high: { text: "Alta confianza", className: "bg-emerald-100 text-emerald-900" },
  medium: { text: "Confianza media", className: "bg-amber-100 text-amber-950" },
  low: { text: "Baja confianza", className: "bg-rose-100 text-rose-900" },
};

function InfoBlock({ icon: Icon, title, children }) {
  if (!children) return null;
  return (
    <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-4 w-4 text-neutral-700" />
        <h4 className="text-sm font-semibold text-neutral-900">{title}</h4>
      </div>
      <div className="text-sm leading-relaxed text-neutral-800">{children}</div>
    </div>
  );
}

function TagList({ items, variant }) {
  if (!items?.length) return null;
  const colors =
    variant === "pro"
      ? "border-emerald-200 bg-emerald-50 text-emerald-950"
      : "border-rose-200 bg-rose-50 text-rose-950";

  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className={clsx("rounded-lg border px-3 py-2 text-sm", colors)}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function OfferResearchPanel({ research, loading }) {
  if (loading) {
    return (
      <section className="panel">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
          <p className="text-neutral-800">Investigando empresa, salarios y opiniones…</p>
        </div>
        <div className="mt-4 space-y-3">
          <div className="skeleton h-4 w-3/4 rounded" />
          <div className="skeleton h-4 w-full rounded" />
          <div className="skeleton h-4 w-5/6 rounded" />
        </div>
      </section>
    );
  }

  if (!research) return null;

  const confidence = CONFIDENCE_LABELS[research.research_confidence] || CONFIDENCE_LABELS.medium;

  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="panel">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-neutral-700" />
            <h3 className="text-xl font-bold text-neutral-900">
              {research.company_name || "Empresa"}
            </h3>
          </div>
          {research.job_title && (
            <p className="mt-1 text-sm text-neutral-700">Puesto: {research.job_title}</p>
          )}
          {research.location && (
            <p className="mt-0.5 flex items-center gap-1 text-sm text-neutral-600">
              <MapPin className="h-3.5 w-3.5" />
              {research.location}
            </p>
          )}
        </div>
        <span className={clsx("rounded-full px-3 py-1 text-xs font-semibold", confidence.className)}>
          {confidence.text}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <InfoBlock icon={Building2} title="Sobre la empresa">
          {research.company_description}
          {(research.industry || research.company_size || research.headquarters) && (
            <p className="mt-2 text-xs text-neutral-600">
              {[research.industry, research.company_size, research.headquarters]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </InfoBlock>

        <InfoBlock icon={Wallet} title="Salario">
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">
                En esta empresa
              </p>
              <p className="mt-1 text-neutral-900">
                {research.salary_company_estimate ||
                  research.salary_estimate ||
                  "No encontrado"}
              </p>
            </div>

            {(research.salary_location_market || research.location) && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">
                  Mercado en {research.location || "la zona"}
                </p>
                <p className="mt-1 text-neutral-900">
                  {research.salary_location_market || "No encontrado"}
                </p>
              </div>
            )}

            {research.salary_comparison && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">
                  Comparación
                </p>
                <p className="mt-1 text-neutral-800">{research.salary_comparison}</p>
              </div>
            )}
          </div>
          {research.salary_notes && (
            <p className="mt-3 text-xs italic text-neutral-600">{research.salary_notes}</p>
          )}
        </InfoBlock>

        <InfoBlock icon={Route} title="Ruta profesional">
          {research.career_path}
          {research.career_path_steps?.length > 0 && (
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-neutral-800">
              {research.career_path_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}
        </InfoBlock>

        <InfoBlock icon={Star} title="Cultura y valores">
          {research.culture_and_values}
          {research.company_rating_summary && (
            <p className="mt-2 text-xs font-medium text-amber-900">{research.company_rating_summary}</p>
          )}
        </InfoBlock>
      </div>

      {research.employee_reviews_summary && (
        <div className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <h4 className="mb-2 text-sm font-semibold text-neutral-900">Opiniones de empleados</h4>
          <p className="text-sm text-neutral-800">{research.employee_reviews_summary}</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-emerald-800">
                <ThumbsUp className="h-3.5 w-3.5" /> Pros
              </p>
              <TagList items={research.pros} variant="pro" />
            </div>
            <div>
              <p className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-rose-800">
                <ThumbsDown className="h-3.5 w-3.5" /> Contras
              </p>
              <TagList items={research.cons} variant="con" />
            </div>
          </div>
        </div>
      )}

      {research.recent_news && (
        <div className="mt-4 text-sm text-neutral-800">
          <strong className="text-neutral-900">Noticias recientes: </strong>
          {research.recent_news}
        </div>
      )}

      {research.application_tips && (
        <div className="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-900">
          <strong>Consejo para aplicar: </strong>
          {research.application_tips}
        </div>
      )}

      {research.sources?.length > 0 && (
        <div className="mt-5">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-600">
            Fuentes consultadas
          </h4>
          <ul className="space-y-1.5">
            {research.sources.map((source) => (
              <li key={source.url || source.title}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-800 underline hover:text-neutral-950"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {source.title || source.url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {research.disclaimers && (
        <p className="mt-4 text-xs italic text-neutral-600">{research.disclaimers}</p>
      )}
    </motion.section>
  );
}
