import { Pencil } from "lucide-react";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function CVEditor({ cv, onChange }) {
  const { t } = useI18n();
  if (!cv) return null;

  const update = (patch) => onChange({ ...cv, ...patch });

  const updateContact = (field, value) => {
    onChange({ ...cv, contact: { ...cv.contact, [field]: value } });
  };

  const updateSkills = (value) => {
    const skills = value
      .split("\n")
      .map((skill) => skill.trim())
      .filter(Boolean);
    onChange({ ...cv, skills });
  };

  const updateBullet = (expIndex, bulletIndex, value) => {
    const experience = cv.experience.map((item, index) => {
      if (index !== expIndex) return item;
      const bullets = [...item.bullets];
      bullets[bulletIndex] = value;
      return { ...item, bullets };
    });
    onChange({ ...cv, experience });
  };

  const updateEducation = (eduIndex, field, value) => {
    const education = cv.education.map((item, index) => {
      if (index !== eduIndex) return item;
      return { ...item, [field]: value };
    });
    onChange({ ...cv, education });
  };

  const inputClass =
    "w-full rounded-xl border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 placeholder-slate-500 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30";

  const contact = cv.contact || {};

  return (
    <article className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-6 backdrop-blur-sm">
      <div className="mb-5 flex items-center gap-2 text-sm text-slate-400">
        <Pencil className="h-4 w-4 text-indigo-400" />
        {t("editor.hint")}
      </div>

      <section className="mb-5">
        <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
          {t("editor.contact")}
        </h4>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.fullName")}</label>
            <input
              className={inputClass}
              value={contact.full_name || ""}
              onChange={(e) => updateContact("full_name", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.headline")}</label>
            <input
              className={inputClass}
              value={contact.headline || ""}
              onChange={(e) => updateContact("headline", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.email")}</label>
            <input
              className={inputClass}
              value={contact.email || ""}
              onChange={(e) => updateContact("email", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.phone")}</label>
            <input
              className={inputClass}
              value={contact.phone || ""}
              onChange={(e) => updateContact("phone", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.location")}</label>
            <input
              className={inputClass}
              value={contact.location || ""}
              onChange={(e) => updateContact("location", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.github")}</label>
            <input
              className={inputClass}
              placeholder="tu-usuario"
              value={contact.github || ""}
              onChange={(e) => updateContact("github", e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">{t("editor.linkedin")}</label>
            <input
              className={inputClass}
              value={contact.linkedin || ""}
              onChange={(e) => updateContact("linkedin", e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs text-slate-500">{t("editor.website")}</label>
            <input
              className={inputClass}
              value={contact.website || ""}
              onChange={(e) => updateContact("website", e.target.value)}
            />
          </div>
        </div>
      </section>

      <section className="mb-5">
        <label htmlFor="edit-summary" className="mb-2 block text-sm font-medium text-slate-300">
          {t("editor.summary")}
        </label>
        <textarea
          id="edit-summary"
          rows={5}
          className={inputClass}
          value={cv.summary}
          onChange={(e) => update({ summary: e.target.value })}
        />
      </section>

      <section className="mb-5">
        <label htmlFor="edit-skills" className="mb-2 block text-sm font-medium text-slate-300">
          {t("editor.skills")}
        </label>
        <textarea
          id="edit-skills"
          rows={6}
          className={inputClass}
          value={(cv.skills || []).join("\n")}
          onChange={(e) => updateSkills(e.target.value)}
        />
      </section>

      {cv.experience?.map((item, expIndex) => (
        <section key={`${item.role}-${expIndex}`} className="mb-5">
          <h4 className="mb-3 font-semibold text-white">
            {item.role}
            {item.company ? ` — ${item.company}` : ""}
          </h4>
          {item.bullets?.map((bullet, bulletIndex) => (
            <div key={`${bullet}-${bulletIndex}`} className="mb-2">
              <label className="mb-1 block text-xs text-slate-500">
                {t("editor.bullet")} {bulletIndex + 1}
              </label>
              <textarea
                rows={2}
                className={inputClass}
                value={bullet}
                onChange={(e) => updateBullet(expIndex, bulletIndex, e.target.value)}
              />
            </div>
          ))}
        </section>
      ))}

      {cv.education?.length > 0 && (
        <section className="mb-2">
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            {t("editor.education")}
          </h4>
          {cv.education.map((item, eduIndex) => (
            <div key={`${item.degree}-${eduIndex}`} className="mb-4 grid gap-3 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-slate-500">{t("editor.degree")}</label>
                <input
                  className={inputClass}
                  value={item.degree || ""}
                  onChange={(e) => updateEducation(eduIndex, "degree", e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">{t("editor.school")}</label>
                <input
                  className={inputClass}
                  value={item.school || ""}
                  onChange={(e) => updateEducation(eduIndex, "school", e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">{t("editor.period")}</label>
                <input
                  className={inputClass}
                  value={item.period || ""}
                  onChange={(e) => updateEducation(eduIndex, "period", e.target.value)}
                />
              </div>
            </div>
          ))}
        </section>
      )}
    </article>
  );
}
