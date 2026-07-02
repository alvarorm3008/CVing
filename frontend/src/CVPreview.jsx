import { BadgeCheck, ExternalLink } from "lucide-react";
import { getCvLabels } from "./cvLabels.js";

function ContactLine({ contact }) {
  const links = [];

  if (contact.email) {
    links.push(
      <a key="email" href={`mailto:${contact.email}`} className="text-neutral-800 underline hover:text-neutral-950">
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
      <a key="linkedin" href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-neutral-800 underline hover:text-neutral-950">
        LinkedIn <ExternalLink className="h-3 w-3" />
      </a>,
    );
  }
  if (contact.github) {
    const raw = contact.github.startsWith("http") ? contact.github : `https://github.com/${contact.github.replace(/^@/, "")}`;
    links.push(
      <a key="github" href={raw} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-neutral-800 underline hover:text-neutral-950">
        GitHub <ExternalLink className="h-3 w-3" />
      </a>,
    );
  }
  if (contact.website) {
    const href = contact.website.startsWith("http") ? contact.website : `https://${contact.website}`;
    links.push(
      <a key="web" href={href} target="_blank" rel="noopener noreferrer" className="text-neutral-800 underline hover:text-neutral-950">
        {contact.website.replace(/^https?:\/\//, "")}
      </a>,
    );
  }

  if (!links.length) return null;
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-neutral-600">
      {links.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span className="text-neutral-400">·</span>}
          {item}
        </span>
      ))}
    </p>
  );
}

function Section({ title, adapted, adaptedLabel, children }) {
  return (
    <section className="border-t border-neutral-200 pt-5 first:border-0 first:pt-0">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-800">{title}</h3>
        {adapted && (
          <span className="flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700">
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
  if (!cv) return null;

  const labels = getCvLabels(cv.document_language);
  const adaptedLabel = labels.adapted;

  return (
    <article className="rounded-2xl border border-neutral-200 bg-white p-8 text-neutral-900 shadow-sm">
      <header className="border-b border-neutral-200 pb-5 text-center">
        <h2 className="text-2xl font-bold text-neutral-900">
          {cv.contact.full_name || labels.defaultName}
        </h2>
        {cv.contact.headline && (
          <p className="mt-1 text-base text-neutral-600">{cv.contact.headline}</p>
        )}
        <ContactLine contact={cv.contact} />
      </header>

      <div className="mt-5 space-y-5">
        {cv.summary && (
          <Section title={labels.summary} adapted adaptedLabel={adaptedLabel}>
            <p className="leading-relaxed text-neutral-600">{cv.summary}</p>
          </Section>
        )}

        {cv.skills?.length > 0 && (
          <Section title={labels.skills} adapted adaptedLabel={adaptedLabel}>
            <div className="flex flex-wrap gap-2">
              {cv.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-neutral-100 px-3 py-1 text-sm font-medium text-neutral-800"
                >
                  {skill}
                </span>
              ))}
            </div>
          </Section>
        )}

        {cv.experience?.length > 0 && (
          <Section title={labels.experience} adapted adaptedLabel={adaptedLabel}>
            {cv.experience.map((item, index) => (
              <div key={`${item.role}-${index}`} className="mb-4 last:mb-0">
                <h4 className="font-semibold text-neutral-900">
                  {item.role}
                  {item.company ? ` — ${item.company}` : ""}
                </h4>
                {(item.period || item.location) && (
                  <p className="text-sm text-neutral-500">
                    {[item.period, item.location].filter(Boolean).join(" | ")}
                  </p>
                )}
                {item.bullets?.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-neutral-600">
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
          <Section title={labels.education}>
            {cv.education.map((item, index) => (
              <div key={`${item.degree}-${index}`} className="mb-2">
                <h4 className="font-semibold">
                  {item.degree}
                  {item.school ? ` — ${item.school}` : ""}
                </h4>
                {item.period && <p className="text-sm text-neutral-500">{item.period}</p>}
              </div>
            ))}
          </Section>
        )}

        {cv.certifications?.length > 0 && (
          <Section title={labels.certifications}>
            <ul className="list-disc space-y-1 pl-5 text-neutral-600">
              {cv.certifications.map((cert) => (
                <li key={cert}>{cert}</li>
              ))}
            </ul>
          </Section>
        )}

        {cv.languages?.length > 0 && (
          <Section title={labels.languages}>
            <p className="text-neutral-600">{cv.languages.join(", ")}</p>
          </Section>
        )}
      </div>
    </article>
  );
}
