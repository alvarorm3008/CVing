import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

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
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</span>
      </div>
      <div className="rounded-xl border border-slate-700/60 bg-slate-900/80 p-4 text-sm">
        <h4 className="font-bold text-white">{cv.contact?.full_name || "CV"}</h4>
        {cv.summary && (
          <p className="mt-2 line-clamp-3 text-slate-300">{cv.summary}</p>
        )}
        {cv.skills?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {cv.skills.slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300"
              >
                {skill}
              </span>
            ))}
            {cv.skills.length > 8 && (
              <span className="text-xs text-slate-500">+{cv.skills.length - 8}</span>
            )}
          </div>
        )}
        {cv.experience?.[0] && (
          <div className="mt-3 border-t border-slate-700/50 pt-3">
            <p className="font-medium text-slate-200">{cv.experience[0].role}</p>
            {cv.experience[0].bullets?.[0] && (
              <p className="mt-1 line-clamp-2 text-xs text-slate-400">
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
  if (!originalCv || !adaptedCv) return null;

  const changes = countChanges(originalCv, adaptedCv);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-slate-900/90 to-indigo-950/30 p-5 backdrop-blur-sm"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-400" />
          <h3 className="font-semibold text-white">Antes vs después</h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="rounded-full bg-indigo-500/20 px-2.5 py-1 text-indigo-300">
            {changes} sección{changes !== 1 ? "es" : ""} adaptada{changes !== 1 ? "s" : ""}
          </span>
          {boosted && (
            <span className="rounded-full bg-emerald-500/20 px-2.5 py-1 text-emerald-300">
              2ª pasada ATS
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
        <MiniCV cv={originalCv} label="CV original" accent="bg-slate-500" />
        <ArrowRight className="mx-auto hidden h-6 w-6 text-indigo-400 md:block" />
        <MiniCV cv={adaptedCv} label="CV adaptado" accent="bg-indigo-500" />
      </div>
    </motion.section>
  );
}
