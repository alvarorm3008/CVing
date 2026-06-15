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
  high: { text: "Alta confianza", className: "bg-emerald-500/20 text-emerald-300" },
  medium: { text: "Confianza media", className: "bg-amber-500/20 text-amber-300" },
  low: { text: "Baja confianza", className: "bg-rose-500/20 text-rose-300" },
};

function InfoBlock({ icon: Icon, title, children, accent = "text-indigo-400" }) {
  if (!children) return null;
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon className={clsx("h-4 w-4", accent)} />
        <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
      </div>
      <div className="text-sm leading-relaxed text-slate-400">{children}</div>
    </div>
  );
}

function TagList({ items, variant }) {
  if (!items?.length) return null;
  const colors =
    variant === "pro"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : "border-rose-500/30 bg-rose-500/10 text-rose-300";

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
      <section className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
          <p className="text-slate-300">Investigando empresa, salarios y opiniones en internet…</p>
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
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-6 backdrop-blur-sm"
    >
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-indigo-400" />
            <h3 className="text-xl font-bold text-white">
              {research.company_name || "Empresa"}
            </h3>
          </div>
          {research.job_title && (
            <p className="mt-1 text-sm text-slate-400">Puesto: {research.job_title}</p>
          )}
          {research.location && (
            <p className="mt-0.5 flex items-center gap-1 text-sm text-slate-500">
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
            <p className="mt-2 text-xs text-slate-500">
              {[research.industry, research.company_size, research.headquarters]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </InfoBlock>

        <InfoBlock icon={Wallet} title="Salario" accent="text-emerald-400">
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-400/80">
                En esta empresa
              </p>
              <p className="mt-1">
                {research.salary_company_estimate ||
                  research.salary_estimate ||
                  "No encontrado"}
              </p>
            </div>

            {(research.salary_location_market || research.location) && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-sky-400/80">
                  Mercado en {research.location || "la zona"}
                </p>
                <p className="mt-1">
                  {research.salary_location_market || "No encontrado"}
                </p>
              </div>
            )}

            {research.salary_comparison && (
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300/90">
                  Comparación
                </p>
                <p className="mt-1 text-slate-300">{research.salary_comparison}</p>
              </div>
            )}
          </div>
          {research.salary_notes && (
            <p className="mt-3 text-xs italic text-slate-500">{research.salary_notes}</p>
          )}
        </InfoBlock>

        <InfoBlock icon={Route} title="Ruta profesional" accent="text-violet-400">
          {research.career_path}
          {research.career_path_steps?.length > 0 && (
            <ol className="mt-2 list-decimal space-y-1 pl-4">
              {research.career_path_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}
        </InfoBlock>

        <InfoBlock icon={Star} title="Cultura y valores">
          {research.culture_and_values}
          {research.company_rating_summary && (
            <p className="mt-2 text-xs text-amber-300">{research.company_rating_summary}</p>
          )}
        </InfoBlock>
      </div>

      {research.employee_reviews_summary && (
        <div className="mt-4 rounded-xl border border-slate-700/50 bg-slate-800/30 p-4">
          <h4 className="mb-2 text-sm font-semibold text-slate-200">Opiniones de empleados</h4>
          <p className="text-sm text-slate-400">{research.employee_reviews_summary}</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-emerald-400">
                <ThumbsUp className="h-3.5 w-3.5" /> Pros
              </p>
              <TagList items={research.pros} variant="pro" />
            </div>
            <div>
              <p className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase text-rose-400">
                <ThumbsDown className="h-3.5 w-3.5" /> Contras
              </p>
              <TagList items={research.cons} variant="con" />
            </div>
          </div>
        </div>
      )}

      {research.recent_news && (
        <div className="mt-4 text-sm text-slate-400">
          <strong className="text-slate-300">Noticias recientes: </strong>
          {research.recent_news}
        </div>
      )}

      {research.application_tips && (
        <div className="mt-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-sm text-indigo-200">
          <strong>Consejo para aplicar: </strong>
          {research.application_tips}
        </div>
      )}

      {research.sources?.length > 0 && (
        <div className="mt-5">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Fuentes consultadas
          </h4>
          <ul className="space-y-1.5">
            {research.sources.map((source) => (
              <li key={source.url || source.title}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-indigo-400 hover:text-indigo-300"
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
        <p className="mt-4 text-xs italic text-slate-600">{research.disclaimers}</p>
      )}
    </motion.section>
  );
}
