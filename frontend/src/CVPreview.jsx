import { BadgeCheck, ExternalLink } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";

function ContactLine({ contact }) {
  const links = [];

  if (contact.email) {
    links.push(
      <a key="email" href={`mailto:${contact.email}`} className="text-indigo-600 hover:underline">
        {contact.email}
      </a>,
    );
  }
  if (contact.phone) {
    links.push(<span key="phone">{contact.phone}</span>);
  }
  if (contact.location) {
    links.push(<span key="location">{contact.location}</span>);
  }
  if (contact.linkedin) {
    const href = contact.linkedin.startsWith("http") ? contact.linkedin : `https://${contact.linkedin}`;
    links.push(
      <a key="linkedin" href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-indigo-600 hover:underline">
        LinkedIn <ExternalLink className="h-3 w-3" />
      </a>,
    );
  }
  if (contact.github) {
    const raw = contact.github.startsWith("http") ? contact.github : `https://github.com/${contact.github.replace(/^@/, "")}`;
    links.push(
      <a key="github" href={raw} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-indigo-600 hover:underline">
        GitHub <ExternalLink className="h-3 w-3" />
      </a>,
    );
  }
  if (contact.website) {
    const href = contact.website.startsWith("http") ? contact.website : `https://${contact.website}`;
    links.push(
      <a key="web" href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
        {contact.website.replace(/^https?:\/\//, "")}
      </a>,
    );
  }

  if (!links.length) return null;
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
      {links.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span className="text-slate-300">·</span>}
          {item}
        </span>
      ))}
    </p>
  );
}

function Section({ title, adapted, adaptedLabel, children }) {
  return (
    <section className="border-t border-slate-700/50 pt-5 first:border-0 first:pt-0">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400">{title}</h3>
        {adapted && (
          <span className="flex items-center gap-1 rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs text-indigo-300">
            <BadgeCheck className="h-3 w-3" />
            {adaptedLabel}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

export default function CVPreview({ cv }) {
  const { t } = useI18n();
  if (!cv) return null;

  const adaptedLabel = t("preview.adapted");

  return (
    <article className="rounded-2xl border border-slate-700/60 bg-white p-8 text-slate-800 shadow-xl shadow-indigo-500/5">
      <header className="border-b border-slate-200 pb-5 text-center">
        <h2 className="text-2xl font-bold text-slate-900">
          {cv.contact.full_name || t("preview.defaultName")}
        </h2>
        {cv.contact.headline && (
          <p className="mt-1 text-base text-slate-600">{cv.contact.headline}</p>
        )}
        <ContactLine contact={cv.contact} />
      </header>

      <div className="mt-5 space-y-5">
        {cv.summary && (
          <Section title={t("preview.summary")} adapted adaptedLabel={adaptedLabel}>
            <p className="leading-relaxed text-slate-600">{cv.summary}</p>
          </Section>
        )}

        {cv.skills?.length > 0 && (
          <Section title={t("preview.skills")} adapted adaptedLabel={adaptedLabel}>
            <div className="flex flex-wrap gap-2">
              {cv.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700"
                >
                  {skill}
                </span>
              ))}
            </div>
          </Section>
        )}

        {cv.experience?.length > 0 && (
          <Section title={t("preview.experience")} adapted adaptedLabel={adaptedLabel}>
            {cv.experience.map((item, index) => (
              <div key={`${item.role}-${index}`} className="mb-4 last:mb-0">
                <h4 className="font-semibold text-slate-900">
                  {item.role}
                  {item.company ? ` — ${item.company}` : ""}
                </h4>
                {(item.period || item.location) && (
                  <p className="text-sm text-slate-500">
                    {[item.period, item.location].filter(Boolean).join(" | ")}
                  </p>
                )}
                {item.bullets?.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-600">
                    {item.bullets.map((bullet, bulletIndex) => (
                      <li key={`${bullet}-${bulletIndex}`}>{bullet}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </Section>
        )}

        {cv.education?.length > 0 && (
          <Section title={t("preview.education")}>
            {cv.education.map((item, index) => (
              <div key={`${item.degree}-${index}`} className="mb-2">
                <h4 className="font-semibold">
                  {item.degree}
                  {item.school ? ` — ${item.school}` : ""}
                </h4>
                {item.period && <p className="text-sm text-slate-500">{item.period}</p>}
              </div>
            ))}
          </Section>
        )}

        {cv.certifications?.length > 0 && (
          <Section title={t("preview.certifications")}>
            <ul className="list-disc space-y-1 pl-5 text-slate-600">
              {cv.certifications.map((cert) => (
                <li key={cert}>{cert}</li>
              ))}
            </ul>
          </Section>
        )}

        {cv.languages?.length > 0 && (
          <Section title={t("preview.languages")}>
            <p className="text-slate-600">{cv.languages.join(", ")}</p>
          </Section>
        )}
      </div>
    </article>
  );
}
