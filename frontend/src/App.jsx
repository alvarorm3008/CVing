import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  Eye,
  FileText,
  Loader2,
  Mail,
  Pencil,
  RefreshCw,
  Rocket,
  Sparkles,
  Target,
  Upload,
} from "lucide-react";
import clsx from "clsx";
import ApplicationProgress from "./ApplicationProgress.jsx";
import ApplicationReadyBanner, { downloadLetterText } from "./ApplicationReadyBanner.jsx";
import ATSMatchPanel from "./ATSMatchPanel.jsx";
import ComparisonPanel from "./ComparisonPanel.jsx";
import CoverLetterPanel from "./CoverLetterPanel.jsx";
import CVEditor from "./CVEditor.jsx";
import CVPreview from "./CVPreview.jsx";
import HistoryPanel from "./HistoryPanel.jsx";
import OfferResearchPanel from "./OfferResearchPanel.jsx";
import { useI18n } from "./i18n/I18nContext.jsx";
import {
  addHistoryEntry,
  clearCvBase,
  clearHistory,
  DATE_LOCALE_MAP,
  deleteHistoryEntry,
  formatDate,
  loadCvBase,
  loadHistory,
  saveCvBase,
} from "./storage.js";

const API_URL = "http://localhost:8000";
const ADAPTATION_MODE = "ats-perfect";
const AI_PROVIDER = "gemini";
const TEMPLATE_ID = "modern-pro";
const ATS_TEMPLATE_ID = "ats-plain";

const OUTPUT_LANGUAGE_OPTIONS = [
  { id: "auto", labelKey: "language.auto" },
  { id: "es", label: "Español" },
  { id: "en", label: "English" },
  { id: "fr", label: "Français" },
  { id: "de", label: "Deutsch" },
  { id: "pt", label: "Português" },
  { id: "it", label: "Italiano" },
  { id: "ca", label: "Català" },
];

async function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function downloadPdfFromBase64(base64, filename) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function renderPdf(cv, templateId, filename) {
  const response = await fetch(`${API_URL}/render-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv, template_id: templateId, filename }),
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "No se pudo generar el PDF");
  }

  const blob = await response.blob();
  const base64 = await blobToBase64(blob);
  return { base64, filename };
}

async function renderAtsTxt(cv) {
  const response = await fetch(`${API_URL}/render-txt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cv }),
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "No se pudo generar el TXT ATS");
  }

  return response.text();
}

function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function Card({ children, className }) {
  return (
    <section
      className={clsx(
        "rounded-2xl border border-slate-700/60 bg-slate-900/50 p-6 backdrop-blur-sm",
        className,
      )}
    >
      {children}
    </section>
  );
}

function Label({ children, htmlFor }) {
  return (
    <label
      htmlFor={htmlFor}
      className="mb-2 block text-sm font-semibold uppercase tracking-wider text-slate-400"
    >
      {children}
    </label>
  );
}

function App() {
  const { t, locale, setLocale, uiLanguages } = useI18n();
  const [jobDescription, setJobDescription] = useState("");
  const [cvFile, setCvFile] = useState(null);
  const [cvBase, setCvBase] = useState(null);
  const [history, setHistory] = useState([]);
  const [cvData, setCvData] = useState(null);
  const [originalCv, setOriginalCv] = useState(null);
  const [boosted, setBoosted] = useState(false);
  const [atsMatch, setAtsMatch] = useState(null);
  const [pdfData, setPdfData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reboosting, setReboosting] = useState(false);
  const [savingBase, setSavingBase] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState("");
  const [showEditor, setShowEditor] = useState(false);
  const [cvDirty, setCvDirty] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [offerResearch, setOfferResearch] = useState(null);
  const [coverLetter, setCoverLetter] = useState(null);
  const [fullAppLoading, setFullAppLoading] = useState(false);
  const [fastMode, setFastMode] = useState(true);
  const [outputLanguage, setOutputLanguage] = useState("auto");
  const [translateContent, setTranslateContent] = useState(false);
  const [applicationReady, setApplicationReady] = useState(false);
  const fileInputRef = useRef(null);

  const hasCvSource = Boolean(cvFile || cvBase);
  const dateLocale = DATE_LOCALE_MAP[locale] || "es-ES";
  const canReboost = atsMatch?.adaptation_mode === "ats-perfect" || true;

  const handleCvChange = (updated) => {
    setCvData(updated);
    setCvDirty(true);
  };

  useEffect(() => {
    setCvBase(loadCvBase());
    setHistory(loadHistory());

    fetch(`${API_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  const acceptCvFile = (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) return;
    setCvFile(file);
    setError("");
  };

  const handleFileChange = (event) => {
    acceptCvFile(event.target.files?.[0] ?? null);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    acceptCvFile(event.dataTransfer.files?.[0]);
  };

  const handleSaveCvBase = async () => {
    if (!cvFile) {
      setError(t("errors.uploadRequired"));
      return;
    }

    setSavingBase(true);
    setError("");

    const formData = new FormData();
    formData.append("cv_file", cvFile);
    formData.append("ai_provider", AI_PROVIDER);

    try {
      const response = await fetch(`${API_URL}/parse-cv`, { method: "POST", body: formData });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t("errors.parseFailed"));
      }

      const saved = saveCvBase({ cv: data.cv, filename: data.filename || cvFile.name });
      setCvBase(saved);
      setCvFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err.message || t("errors.saveBaseFailed"));
    } finally {
      setSavingBase(false);
    }
  };

  const handleRemoveCvBase = () => {
    clearCvBase();
    setCvBase(null);
  };

  const applyFullResponse = (data, jobDesc) => {
    setCvData(data.cv);
    setOriginalCv(data.original_cv);
    setBoosted(data.boosted || false);
    setAtsMatch(data.ats_match);
    setOfferResearch(data.research);
    setCoverLetter(data.cover_letter);
    setPdfData({
      base64: data.pdf_base64,
      filename: data.pdf_filename || "cv-adaptado.pdf",
    });
    setShowEditor(false);
    setCvDirty(false);
    setApplicationReady(true);

    const updatedHistory = addHistoryEntry({
      jobDescription: jobDesc,
      cv: data.cv,
      original_cv: data.original_cv,
      ats_match: data.ats_match,
      template_id: TEMPLATE_ID,
      pdf_filename: data.pdf_filename,
      adaptation_mode: ADAPTATION_MODE,
      honest_score: data.ats_match?.honest_score,
      boosted: data.boosted,
      offer_research: data.research,
      cover_letter: data.cover_letter,
      personal_interests: "",
      full_application: true,
    });
    setHistory(updatedHistory);
  };

  const applyAdaptResponse = (data, jobDesc) => {
    setApplicationReady(false);
    setCvData(data.cv);
    setOriginalCv(data.original_cv);
    setBoosted(data.boosted || false);
    setAtsMatch(data.ats_match);
    setPdfData({
      base64: data.pdf_base64,
      filename: data.pdf_filename || "cv-adaptado.pdf",
    });
    setShowEditor(false);
    setCvDirty(false);

    const updatedHistory = addHistoryEntry({
      jobDescription: jobDesc,
      cv: data.cv,
      original_cv: data.original_cv,
      ats_match: data.ats_match,
      template_id: TEMPLATE_ID,
      pdf_filename: data.pdf_filename,
      adaptation_mode: ADAPTATION_MODE,
      honest_score: data.ats_match?.honest_score,
      boosted: data.boosted,
      offer_research: offerResearch,
      cover_letter: coverLetter,
    });
    setHistory(updatedHistory);
  };

  const handleFullApplication = async () => {
    if (!jobDescription.trim()) {
      setError(t("errors.jobRequired"));
      return;
    }
    if (!hasCvSource) {
      setError(t("errors.cvRequired"));
      return;
    }

    setFullAppLoading(true);
    setApplicationReady(false);
    setError("");
    setCvData(null);
    setOriginalCv(null);
    setAtsMatch(null);
    setPdfData(null);
    setOfferResearch(null);
    setCoverLetter(null);
    setCvDirty(false);

    const formData = buildAdaptFormData();
    formData.append("fast_mode", fastMode ? "true" : "false");

    try {
      const response = await fetch(`${API_URL}/full-application`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item) => item.msg).join(", ")
          : data.detail;
        throw new Error(detail || t("errors.fullAppFailed"));
      }

      applyFullResponse(data, jobDescription);
    } catch (err) {
      setError(err.message || t("errors.fullAppFailed"));
    } finally {
      setFullAppLoading(false);
    }
  };

  const buildAdaptFormData = (options = {}) => {
    const { reboost = false, useCurrentCv = false } = options;
    const formData = new FormData();
    formData.append("job_description", jobDescription);
    formData.append("template_id", TEMPLATE_ID);
    formData.append("adaptation_mode", ADAPTATION_MODE);
    formData.append("output_language", outputLanguage);
    formData.append("translate_content", translateContent ? "true" : "false");
    formData.append("ai_provider", AI_PROVIDER);
    if (reboost) formData.append("reboost", "true");

    if (useCurrentCv && cvData) {
      formData.append("cv_json", JSON.stringify(cvData));
      if (originalCv) {
        formData.append("base_cv_json", JSON.stringify(originalCv));
      }
      formData.append("source_filename", pdfData?.filename || "cv-adaptado.pdf");
    } else if (cvFile) {
      formData.append("cv_file", cvFile);
    } else if (cvBase) {
      formData.append("cv_json", JSON.stringify(cvBase.cv));
      formData.append("source_filename", cvBase.filename);
    }
    return formData;
  };

  const handleAdapt = async () => {
    if (!jobDescription.trim()) {
      setError(t("errors.jobRequired"));
      return;
    }
    if (!hasCvSource) {
      setError(t("errors.cvRequired"));
      return;
    }

    setLoading(true);
    setError("");
    setCvDirty(false);
    setApplicationReady(false);
    setCvData(null);
    setOriginalCv(null);
    setAtsMatch(null);
    setPdfData(null);

    try {
      const response = await fetch(`${API_URL}/adapt-cv`, {
        method: "POST",
        body: buildAdaptFormData(),
      });
      const data = await response.json();

      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((item) => item.msg).join(", ")
          : data.detail;
        throw new Error(detail || t("errors.adaptFailed"));
      }

      applyAdaptResponse(data, jobDescription);
    } catch (err) {
      setError(err.message || t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  const handleReboost = async () => {
    if (!cvData || !jobDescription.trim()) return;

    setReboosting(true);
    setError("");

    const formData = buildAdaptFormData({ reboost: true, useCurrentCv: true });
    formData.set("adaptation_mode", "ats-perfect");

    try {
      const response = await fetch(`${API_URL}/adapt-cv`, { method: "POST", body: formData });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || t("errors.reboostFailed"));
      }

      applyAdaptResponse(data, jobDescription);
    } catch (err) {
      setError(err.message || t("errors.reboostFailed"));
    } finally {
      setReboosting(false);
    }
  };

  const handleUpdatePdf = async () => {
    if (!cvData) return;
    setRendering(true);
    setError("");
    try {
      const pdf = await renderPdf(cvData, TEMPLATE_ID, pdfData?.filename || "cv-adaptado.pdf");
      setPdfData(pdf);
      setCvDirty(false);
    } catch (err) {
      setError(err.message || t("errors.updatePdfFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!cvData) return;
    setRendering(true);
    setError("");
    try {
      let pdf = pdfData;
      if (cvDirty || !pdf) {
        pdf = await renderPdf(cvData, TEMPLATE_ID, pdfData?.filename || "cv-adaptado.pdf");
        setPdfData(pdf);
        setCvDirty(false);
      }
      downloadPdfFromBase64(pdf.base64, pdf.filename);
    } catch (err) {
      setError(err.message || t("errors.downloadFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleDownloadAtsPdf = async () => {
    if (!cvData) return;
    setRendering(true);
    setError("");
    try {
      const baseName = (pdfData?.filename || "cv-adaptado.pdf").replace(/\.pdf$/i, "");
      const pdf = await renderPdf(cvData, ATS_TEMPLATE_ID, `${baseName}-ats.pdf`);
      downloadPdfFromBase64(pdf.base64, pdf.filename);
    } catch (err) {
      setError(err.message || t("errors.downloadAtsFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleDownloadAtsTxt = async () => {
    if (!cvData) return;
    setRendering(true);
    setError("");
    try {
      const baseName = (pdfData?.filename || "cv-adaptado.pdf").replace(/\.pdf$/i, "");
      const text = await renderAtsTxt(cvData);
      downloadTextFile(text, `${baseName}-ats.txt`);
    } catch (err) {
      setError(err.message || t("errors.downloadAtsTxtFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleHistorySelect = async (entry) => {
    setJobDescription(entry.jobDescription);
    setCvData(entry.cv);
    setOriginalCv(entry.original_cv || null);
    setBoosted(entry.boosted || false);
    setAtsMatch(entry.ats_match);
    setOfferResearch(entry.offer_research || null);
    setCoverLetter(entry.cover_letter || null);
    setApplicationReady(Boolean(entry.full_application));
    setShowEditor(false);
    setCvDirty(false);
    setError("");
    setRendering(true);
    try {
      const pdf = await renderPdf(entry.cv, TEMPLATE_ID, entry.pdf_filename || "cv-adaptado.pdf");
      setPdfData(pdf);
    } catch (err) {
      setError(err.message || t("errors.historyPdfFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleHistoryDelete = (id) => {
    setHistory(deleteHistoryEntry(id));
  };

  const handleHistoryClear = () => {
    clearHistory();
    setHistory([]);
  };

  const inputClass =
    "w-full rounded-xl border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 placeholder-slate-500 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30";

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10 text-center"
      >
        <div className="mb-4 flex flex-wrap items-center justify-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-sm text-indigo-300">
            <Sparkles className="h-4 w-4" />
            {t("app.badge")}
          </div>
          <select
            aria-label={t("app.uiLanguage")}
            className="rounded-full border border-slate-600 bg-slate-800/80 px-3 py-1.5 text-sm text-slate-200"
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
          >
            {uiLanguages.map((lang) => (
              <option key={lang.id} value={lang.id}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>
        <h1 className="bg-gradient-to-r from-white via-indigo-200 to-violet-300 bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl">
          {t("app.title")}
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-slate-400">{t("app.subtitle")}</p>
      </motion.header>

      <main className="space-y-6">
        {backendStatus !== "online" && (
          <div
            className={clsx(
              "rounded-xl border px-4 py-3 text-sm",
              backendStatus === "checking" && "border-slate-600 bg-slate-800/60 text-slate-400",
              backendStatus === "offline" && "border-rose-500/40 bg-rose-500/10 text-rose-300",
            )}
            role="status"
          >
            {backendStatus === "checking" ? t("backend.checking") : t("backend.offline")}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <Label htmlFor="job-description">{t("job.label")}</Label>
            <textarea
              id="job-description"
              className={clsx(inputClass, "min-h-[220px] resize-y")}
              placeholder={t("job.placeholder")}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={10}
            />
          </Card>

          <Card>
            <Label htmlFor="cv-pdf">{t("cv.label")}</Label>

            {cvBase && (
              <div className="mb-4 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                <div>
                  <p className="flex items-center gap-2 font-semibold text-emerald-300">
                    <FileText className="h-4 w-4" />
                    {t("cv.saved")}
                  </p>
                  <p className="text-sm text-slate-400">
                    {cvBase.filename} · {formatDate(cvBase.savedAt, dateLocale)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveCvBase}
                  className="text-sm text-slate-400 hover:text-rose-400"
                >
                  {t("cv.remove")}
                </button>
              </div>
            )}

            <input
              ref={fileInputRef}
              id="cv-pdf"
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              className="hidden"
            />
            <div
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={clsx(
                "flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-8 text-slate-300 transition",
                dragOver
                  ? "border-indigo-400 bg-indigo-500/10"
                  : "border-slate-600 bg-slate-800/40 hover:border-indigo-500/50 hover:bg-slate-800/60",
              )}
            >
              <Upload className="h-5 w-5 text-indigo-400" />
              {cvFile ? cvFile.name : t("cv.upload")}
            </div>

            <button
              type="button"
              onClick={handleSaveCvBase}
              disabled={!cvFile || savingBase || loading}
              className="mt-3 w-full rounded-xl border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-40"
            >
              {savingBase ? t("cv.saving") : t("cv.saveBase")}
            </button>
          </Card>
        </div>

        <Card>
          <Label htmlFor="output-language">{t("language.outputLabel")}</Label>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <select
                id="output-language"
                className={inputClass}
                value={outputLanguage}
                onChange={(e) => setOutputLanguage(e.target.value)}
                disabled={loading || fullAppLoading}
              >
                {OUTPUT_LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.id} value={lang.id}>
                    {lang.labelKey ? t(lang.labelKey) : lang.label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-sm text-slate-500">{t("language.hint")}</p>
            </div>
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-700/50 bg-slate-800/40 px-3 py-2.5">
              <input
                type="checkbox"
                checked={translateContent}
                onChange={(e) => setTranslateContent(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
              />
              <span>
                <span className="block text-sm font-medium text-slate-200">{t("language.translate")}</span>
                <span className="block text-xs text-slate-500">{t("language.translateHint")}</span>
              </span>
            </label>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 to-violet-950/30 !p-8">
          <div className="mb-2 flex items-center gap-2">
            <Rocket className="h-6 w-6 text-indigo-400" />
            <h2 className="text-xl font-bold text-white">{t("fullApp.title")}</h2>
          </div>
          <p className="mb-5 text-sm text-slate-400">{t("fullApp.subtitle")}</p>

          <label className="mb-4 flex cursor-pointer items-center gap-3 rounded-xl border border-slate-700/50 bg-slate-800/40 px-4 py-3">
            <input
              type="checkbox"
              checked={fastMode}
              onChange={(e) => setFastMode(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
            />
            <span>
              <span className="block text-sm font-medium text-slate-200">{t("fullApp.fastMode")}</span>
              <span className="block text-xs text-slate-500">{t("fullApp.fastModeHint")}</span>
            </span>
          </label>

          <ApplicationProgress active={fullAppLoading} indeterminate={fullAppLoading} />

          {!fullAppLoading && (
            <button
              type="button"
              onClick={handleFullApplication}
              disabled={loading || rendering || savingBase || !jobDescription.trim() || !hasCvSource}
              className="mt-4 flex w-full items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 px-8 py-4 text-lg font-bold text-white shadow-xl shadow-indigo-500/30 transition hover:brightness-110 disabled:opacity-40 sm:w-auto"
            >
              <Rocket className="h-6 w-6" />
              {t("fullApp.button")}
            </button>
          )}

          {fullAppLoading && (
            <p className="mt-4 text-center text-sm text-slate-500">{t("fullApp.loading")}</p>
          )}
        </Card>

        <Card className="border-violet-500/20 !p-8">
          <div className="mb-2 flex items-center gap-2">
            <Target className="h-6 w-6 text-violet-400" />
            <h2 className="text-xl font-bold text-white">{t("cvOnly.title")}</h2>
          </div>
          <p className="mb-5 text-sm text-slate-400">{t("cvOnly.subtitle")}</p>

          <ApplicationProgress active={loading} indeterminate={loading} />

          {!loading && (
            <button
              type="button"
              onClick={handleAdapt}
              disabled={loading || rendering || savingBase || fullAppLoading || !jobDescription.trim() || !hasCvSource}
              className="mt-4 flex w-full items-center justify-center gap-3 rounded-2xl border border-violet-500/40 bg-violet-500/10 px-8 py-4 text-lg font-bold text-violet-100 transition hover:bg-violet-500/20 disabled:opacity-40"
            >
              <Sparkles className="h-6 w-6" />
              {t("cvOnly.button")}
            </button>
          )}
        </Card>
        </div>

        <Card className="!p-8">
          {error && (
            <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-300" role="alert">
              {error}
            </div>
          )}

          {applicationReady && cvData && offerResearch && coverLetter && (
            <div className="mt-8">
              <ApplicationReadyBanner
                companyName={offerResearch.company_name}
                jobTitle={offerResearch.job_title || atsMatch?.target_role}
                onDownloadCv={handleDownloadPdf}
                onDownloadLetter={() => downloadLetterText(coverLetter)}
                downloading={rendering}
              />
            </div>
          )}

          {cvData && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-8 space-y-6"
            >
              <ComparisonPanel originalCv={originalCv} adaptedCv={cvData} boosted={boosted} />

              {offerResearch && (
                <OfferResearchPanel research={offerResearch} loading={false} />
              )}

              <ATSMatchPanel
                atsMatch={atsMatch}
                onReboost={canReboost ? handleReboost : undefined}
                reboosting={reboosting}
              />

              {coverLetter && (
                <CoverLetterPanel
                  coverLetter={coverLetter}
                  onChange={setCoverLetter}
                  loading={false}
                />
              )}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-lg font-bold text-white">{t("result.title")}</h3>
                  {cvDirty && (
                    <p className="mt-1 text-xs text-amber-400">{t("result.dirtyHint")}</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setShowEditor((v) => !v)}
                    className={clsx(
                      "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
                      showEditor
                        ? "bg-indigo-500/20 text-indigo-300"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700",
                    )}
                  >
                    {showEditor ? <Eye className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                    {showEditor ? t("actions.preview") : t("actions.edit")}
                  </button>
                  <button
                    type="button"
                    onClick={handleUpdatePdf}
                    disabled={rendering}
                    className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                  >
                    <RefreshCw className={clsx("h-4 w-4", rendering && "animate-spin")} />
                    {rendering ? t("result.updating") : t("result.updatePdf")}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    disabled={rendering}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                  >
                    <Download className="h-4 w-4" />
                    {t("actions.download")}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadAtsPdf}
                    disabled={rendering}
                    title={t("actions.downloadAtsHint")}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                  >
                    <FileText className="h-4 w-4" />
                    {t("actions.downloadAts")}
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadAtsTxt}
                    disabled={rendering}
                    title={t("actions.downloadAtsTxtHint")}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                  >
                    <FileText className="h-4 w-4" />
                    {t("actions.downloadAtsTxt")}
                  </button>
                </div>
              </div>

              {showEditor ? (
                <CVEditor cv={cvData} onChange={handleCvChange} />
              ) : (
                <>
                  <p className="mb-3 text-xs text-slate-500">{t("result.previewHint")}</p>
                  <CVPreview cv={cvData} />
                </>
              )}

              {pdfData?.base64 && (
                <div className="overflow-hidden rounded-2xl border border-slate-700/60 bg-slate-900/60">
                  <p className="border-b border-slate-700/60 px-4 py-2 text-xs font-medium uppercase tracking-wider text-slate-500">
                    {t("result.pdfPreview")}
                  </p>
                  <iframe
                    title="PDF preview"
                    src={`data:application/pdf;base64,${pdfData.base64}`}
                    className="h-[600px] w-full bg-white"
                  />
                </div>
              )}
            </motion.div>
          )}

          {!cvData && !loading && !fullAppLoading && (
            <p className="mt-6 text-center text-sm text-slate-500">{t("result.emptyHint")}</p>
          )}
        </Card>

        <HistoryPanel
          history={history}
          onSelect={handleHistorySelect}
          onDelete={handleHistoryDelete}
          onClear={handleHistoryClear}
        />
      </main>

      <footer className="mt-12 pb-8 text-center text-sm text-slate-600">
        {t("footer.poweredBy")} {t("ai.gemini")}
      </footer>
    </div>
  );
}

export default App;
