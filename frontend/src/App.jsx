import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Download,
  Eye,
  FileText,
  Lightbulb,
  Loader2,
  Mail,
  Package,
  Pencil,
  RefreshCw,
  Rocket,
  ScanSearch,
  Sparkles,
  Target,
  Upload,
  Zap,
} from "lucide-react";
import clsx from "clsx";
import ApplicationProgress from "./ApplicationProgress.jsx";
import ApplicationReadyBanner, { downloadLetterText } from "./ApplicationReadyBanner.jsx";
import ATSMatchPanel from "./ATSMatchPanel.jsx";
import ChangesPanel from "./ChangesPanel.jsx";
import ComparisonPanel from "./ComparisonPanel.jsx";
import CoverLetterPanel from "./CoverLetterPanel.jsx";
import CVEditor from "./CVEditor.jsx";
import CVPreview from "./CVPreview.jsx";
import DownloadStickyBar from "./DownloadStickyBar.jsx";
import FlowGuide from "./FlowGuide.jsx";
import HistoryPanel from "./HistoryPanel.jsx";
import OfferResearchPanel from "./OfferResearchPanel.jsx";
import PreflightPanel from "./PreflightPanel.jsx";
import { API_URL, formatApiError, getApiBaseForDisplay, isSplitDeployMisconfigured } from "./api.js";
import { loadDemoData } from "./demoData.js";
import { downloadApplicationPack } from "./downloadPack.js";
import { getFlowStep, getRecommendedAction } from "./flowUtils.js";
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
  isCvContentEmpty,
  cvBaseSummary,
  updateHistoryEntry,
} from "./storage.js";

const AI_PROVIDER = "gemini";
const DEFAULT_TEMPLATE_ID = "modern-pro";
const ATS_TEMPLATE_ID = "ats-plain";

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
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
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
  return { base64: await blobToBase64(blob), filename };
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
  return <section className={clsx("panel", className)}>{children}</section>;
}

function Label({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="mb-2 block text-sm font-semibold text-neutral-800">
      {children}
    </label>
  );
}

function App() {
  const { t, locale, setLocale, uiLanguages } = useI18n();
  const [jobDescription, setJobDescription] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [urlImportLoading, setUrlImportLoading] = useState(false);
  const [cvFile, setCvFile] = useState(null);
  const [cvBase, setCvBase] = useState(null);
  const [history, setHistory] = useState([]);
  const [cvData, setCvData] = useState(null);
  const [originalCv, setOriginalCv] = useState(null);
  const [boosted, setBoosted] = useState(false);
  const [atsMatch, setAtsMatch] = useState(null);
  const [preflight, setPreflight] = useState(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [pdfData, setPdfData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [honestLoading, setHonestLoading] = useState(false);
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
  const [offerLanguage, setOfferLanguage] = useState(null);
  const [applicationReady, setApplicationReady] = useState(false);
  const [lastAction, setLastAction] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [templateId, setTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [templates, setTemplates] = useState([]);
  const [cvParseWarning, setCvParseWarning] = useState("");
  const [adaptationMode, setAdaptationMode] = useState("ats-perfect");
  const fileInputRef = useRef(null);
  const preflightCacheRef = useRef("");

  const hasCvSource = Boolean(cvFile || cvBase || cvData);
  const dateLocale = DATE_LOCALE_MAP[locale] || "es-ES";
  const honestScore = atsMatch?.honest_score ?? atsMatch?.score ?? 0;
  const canReboost =
    Boolean(cvData) &&
    atsMatch?.adaptation_mode === "ats-perfect" &&
    honestScore > 0 &&
    honestScore < 80;

  const flowStep = getFlowStep(lastAction, cvData, coverLetter);
  const { recommendedId } = getRecommendedAction({
    preflight,
    atsMatch,
    lastAction,
    cvData,
    coverLetter,
    hasCvSource,
    jobDescription,
  });

  const handleCvChange = (updated) => {
    setCvData(updated);
    setCvDirty(true);
  };

  const buildCheckFormData = useCallback(() => {
    const formData = new FormData();
    formData.append("job_description", jobDescription);
    if (cvData) {
      formData.append("cv_json", JSON.stringify(cvData));
    } else if (cvBase) {
      formData.append("cv_json", JSON.stringify(cvBase.cv));
    } else if (cvFile) {
      formData.append("cv_file", cvFile);
    }
    return formData;
  }, [jobDescription, cvData, cvBase, cvFile]);

  const parseAndSaveCv = useCallback(
    async (file) => {
      if (!file) return;
      if (backendStatus === "offline") {
        setError(t("cv.backendRequired"));
        setCvFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }
      setSavingBase(true);
      setError("");
      setCvParseWarning("");
      const formData = new FormData();
      formData.append("cv_file", file);
      formData.append("ai_provider", AI_PROVIDER);
      try {
        const response = await fetch(`${API_URL}/parse-cv`, { method: "POST", body: formData });
        let data = {};
        try {
          data = await response.json();
        } catch {
          if (!response.ok) throw new Error(t("errors.parseFailed"));
        }
        if (!response.ok) {
          throw new Error(formatApiError(data.detail, t("errors.parseFailed")));
        }
        if (!data.cv) throw new Error(t("errors.parseFailed"));
        const saved = saveCvBase({ cv: data.cv, filename: data.filename || file.name });
        setCvBase(saved);
        setCvFile(null);
        if (isCvContentEmpty(data.cv)) {
          setCvParseWarning(t("cv.parseEmpty"));
        }
        if (fileInputRef.current) fileInputRef.current.value = "";
      } catch (err) {
        setCvFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        setError(err.message || t("errors.saveBaseFailed"));
      } finally {
        setSavingBase(false);
      }
    },
    [t, backendStatus],
  );

  useEffect(() => {
    const loaded = loadCvBase();
    setCvBase(loaded);
    if (loaded && isCvContentEmpty(loaded.cv)) {
      setCvParseWarning(t("cv.parseEmpty"));
    }
    setHistory(loadHistory());

    let cancelled = false;

    async function checkHealth(attempt = 0) {
      if (cancelled) return;
      if (attempt === 0) setBackendStatus("checking");
      else setBackendStatus("waking");

      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 65000);
        const res = await fetch(`${API_URL}/health`, { signal: controller.signal });
        clearTimeout(timeout);
        if (!res.ok) throw new Error("health failed");
        if (!cancelled) setBackendStatus("online");
      } catch {
        if (cancelled) return;
        if (attempt < 2 && API_URL) {
          setTimeout(() => checkHealth(attempt + 1), 2000);
          return;
        }
        setBackendStatus("offline");
      }
    }

    checkHealth();

    fetch(`${API_URL}/templates`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setTemplates(Array.isArray(data) ? data : []))
      .catch(() => setTemplates([]));

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (cvFile) parseAndSaveCv(cvFile);
  }, [cvFile, parseAndSaveCv]);

  useEffect(() => {
    const text = jobDescription.trim();
    if (text.length < 40) {
      setOfferLanguage(null);
      return undefined;
    }
    const timer = setTimeout(() => {
      const body = new FormData();
      body.append("job_description", text);
      fetch(`${API_URL}/detect-offer-language`, { method: "POST", body })
        .then((res) => (res.ok ? res.json() : Promise.reject()))
        .then((data) => {
          setOfferLanguage(data.language && data.language !== "unknown" ? data : null);
        })
        .catch(() => setOfferLanguage(null));
    }, 400);
    return () => clearTimeout(timer);
  }, [jobDescription]);

  useEffect(() => {
    const job = jobDescription.trim();
    if (job.length < 80 || !hasCvSource) {
      setPreflight(null);
      return undefined;
    }
    const cacheKey = `${job.length}:${cvData?.contact?.full_name || ""}:${cvBase?.filename || ""}`;
    if (cacheKey === preflightCacheRef.current && preflight) return undefined;

    const timer = setTimeout(async () => {
      setPreflightLoading(true);
      try {
        const response = await fetch(`${API_URL}/check-ats`, {
          method: "POST",
          body: buildCheckFormData(),
        });
        const data = await response.json();
        if (response.ok) {
          preflightCacheRef.current = cacheKey;
          setPreflight(data);
        }
      } catch {
        /* ignore background preflight errors */
      } finally {
        setPreflightLoading(false);
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [jobDescription, hasCvSource, cvData, cvBase, buildCheckFormData]);

  const acceptCvFile = (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setError(t("cv.invalidFormat"));
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setCvParseWarning("");
    setCvFile(file);
    setError("");
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null;
    event.target.value = "";
    acceptCvFile(file);
  };
  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    acceptCvFile(event.dataTransfer.files?.[0]);
  };

  const handleRemoveCvBase = () => {
    clearCvBase();
    setCvBase(null);
    setCvParseWarning("");
  };

  const handleImportUrl = async () => {
    if (!jobUrl.trim()) return;
    setUrlImportLoading(true);
    setError("");
    try {
      const body = new FormData();
      body.append("url", jobUrl.trim());
      const response = await fetch(`${API_URL}/fetch-job-offer`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || t("urlImport.failed"));
      setJobDescription(data.text || "");
      if (data.warning) setError(data.warning);
    } catch (err) {
      setError(err.message || t("urlImport.failed"));
    } finally {
      setUrlImportLoading(false);
    }
  };

  const handleLoadDemo = () => {
    const demo = loadDemoData();
    setJobDescription(demo.jobDescription);
    const saved = saveCvBase({ cv: demo.cv, filename: demo.filename });
    setCvBase(saved);
    setError("");
  };

  const applyFullResponse = (data, jobDesc) => {
    setCvData(data.cv);
    setOriginalCv(data.original_cv);
    setBoosted(data.boosted || false);
    setAtsMatch(data.ats_match);
    setOfferResearch(data.research);
    setCoverLetter(data.cover_letter);
    setPdfData({ base64: data.pdf_base64, filename: data.pdf_filename || "cv-adaptado.pdf" });
    setShowEditor(false);
    setCvDirty(false);
    setApplicationReady(true);
    setAdaptationMode("ats-perfect");
    setHistory(
      addHistoryEntry({
        jobDescription: jobDesc,
        cv: data.cv,
        original_cv: data.original_cv,
        ats_match: data.ats_match,
        template_id: templateId,
        pdf_filename: data.pdf_filename,
        adaptation_mode: "ats-perfect",
        honest_score: data.ats_match?.honest_score,
        boosted: data.boosted,
        offer_research: data.research,
        cover_letter: data.cover_letter,
        full_application: true,
      }),
    );
  };

  const applyAdaptResponse = (data, jobDesc, mode = "ats-perfect") => {
    setApplicationReady(false);
    setCvData(data.cv);
    setOriginalCv(data.original_cv);
    setBoosted(data.boosted || false);
    setAtsMatch(data.ats_match);
    setPdfData({ base64: data.pdf_base64, filename: data.pdf_filename || "cv-adaptado.pdf" });
    setShowEditor(false);
    setCvDirty(false);
    setAdaptationMode(mode);
    setHistory(
      addHistoryEntry({
        jobDescription: jobDesc,
        cv: data.cv,
        original_cv: data.original_cv,
        ats_match: data.ats_match,
        template_id: templateId,
        pdf_filename: data.pdf_filename,
        adaptation_mode: mode,
        honest_score: data.ats_match?.honest_score,
        boosted: data.boosted,
        offer_research: offerResearch,
        cover_letter: coverLetter,
      }),
    );
  };

  const buildAdaptFormData = (options = {}) => {
    const { reboost = false, useCurrentCv = false, mode = adaptationMode } = options;
    const formData = new FormData();
    formData.append("job_description", jobDescription);
    formData.append("template_id", templateId);
    formData.append("adaptation_mode", mode);
    formData.append("output_language", "auto");
    formData.append("ai_provider", AI_PROVIDER);
    if (reboost) formData.append("reboost", "true");

    if (useCurrentCv && cvData) {
      formData.append("cv_json", JSON.stringify(cvData));
      if (originalCv) formData.append("base_cv_json", JSON.stringify(originalCv));
      formData.append("source_filename", pdfData?.filename || "cv-adaptado.pdf");
    } else if (cvBase) {
      formData.append("cv_json", JSON.stringify(cvBase.cv));
      formData.append("source_filename", cvBase.filename);
    } else if (cvFile) {
      formData.append("cv_file", cvFile);
    } else if (cvData) {
      formData.append("cv_json", JSON.stringify(cvData));
      formData.append("source_filename", pdfData?.filename || "cv-adaptado.pdf");
    }
    return formData;
  };

  const handleLocalAnalysis = async (action) => {
    if (!jobDescription.trim()) {
      setError(t("errors.jobRequired"));
      return;
    }
    if (!hasCvSource) {
      setError(t("errors.cvRequired"));
      return;
    }
    setAnalysisLoading(true);
    setLastAction(action);
    setError("");
    try {
      const response = await fetch(`${API_URL}/check-ats`, { method: "POST", body: buildCheckFormData() });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || t("errors.checkAtsFailed"));
      setAtsMatch(data);
      setPreflight(data);
    } catch (err) {
      setError(err.message || t("errors.checkAtsFailed"));
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleAdapt = async (mode = "ats-perfect") => {
    if (!jobDescription.trim()) {
      setError(t("errors.jobRequired"));
      return;
    }
    if (!hasCvSource) {
      setError(t("errors.cvRequired"));
      return;
    }
    const isHonest = mode === "honest";
    if (isHonest) setHonestLoading(true);
    else setLoading(true);
    setLastAction(isHonest ? "honest" : "adapt");
    setError("");
    setCvDirty(false);
    setApplicationReady(false);
    if (!isHonest) {
      setCvData(null);
      setOriginalCv(null);
      setAtsMatch(null);
      setPdfData(null);
    }
    try {
      const formData = buildAdaptFormData({ mode });
      const response = await fetch(`${API_URL}/adapt-cv`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((i) => i.msg).join(", ") : data.detail;
        throw new Error(detail || t("errors.adaptFailed"));
      }
      applyAdaptResponse(data, jobDescription, mode);
    } catch (err) {
      setError(err.message || t("errors.generic"));
    } finally {
      if (isHonest) setHonestLoading(false);
      else setLoading(false);
    }
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
    setLastAction("full");
    setApplicationReady(false);
    setError("");
    setCvData(null);
    setOriginalCv(null);
    setAtsMatch(null);
    setPdfData(null);
    setOfferResearch(null);
    setCoverLetter(null);
    setCvDirty(false);
    const formData = buildAdaptFormData({ mode: "ats-perfect" });
    formData.append("fast_mode", fastMode ? "true" : "false");
    try {
      const response = await fetch(`${API_URL}/full-application`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((i) => i.msg).join(", ") : data.detail;
        throw new Error(detail || t("errors.fullAppFailed"));
      }
      applyFullResponse(data, jobDescription);
    } catch (err) {
      setError(err.message || t("errors.fullAppFailed"));
    } finally {
      setFullAppLoading(false);
    }
  };

  const handleReboost = async () => {
    if (!cvData || !jobDescription.trim()) return;
    setReboosting(true);
    setError("");
    const formData = buildAdaptFormData({ reboost: true, useCurrentCv: true, mode: "ats-perfect" });
    try {
      const response = await fetch(`${API_URL}/adapt-cv`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || t("errors.reboostFailed"));
      applyAdaptResponse(data, jobDescription, "ats-perfect");
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
      const pdf = await renderPdf(cvData, templateId, pdfData?.filename || "cv-adaptado.pdf");
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
        pdf = await renderPdf(cvData, templateId, pdfData?.filename || "cv-adaptado.pdf");
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

  const handleDownloadPack = async () => {
    if (!cvData) return;
    setRendering(true);
    setError("");
    try {
      await downloadApplicationPack({
        cv: cvData,
        pdfData,
        coverLetter,
        templateId,
        atsTemplateId: ATS_TEMPLATE_ID,
        baseFilename: (pdfData?.filename || "cv-adaptado.pdf").replace(/\.pdf$/i, ""),
      });
    } catch (err) {
      setError(err.message || t("errors.packageFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleDownloadAtsPdf = async () => {
    if (!cvData) return;
    setRendering(true);
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
    try {
      const baseName = (pdfData?.filename || "cv-adaptado.pdf").replace(/\.pdf$/i, "");
      downloadTextFile(await renderAtsTxt(cvData), `${baseName}-ats.txt`);
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
    setTemplateId(entry.template_id || DEFAULT_TEMPLATE_ID);
    setAdaptationMode(entry.adaptation_mode || "ats-perfect");
    setShowEditor(false);
    setCvDirty(false);
    setError("");
    setRendering(true);
    try {
      setPdfData(await renderPdf(entry.cv, entry.template_id || templateId, entry.pdf_filename || "cv-adaptado.pdf"));
    } catch (err) {
      setError(err.message || t("errors.historyPdfFailed"));
    } finally {
      setRendering(false);
    }
  };

  const handleHistoryDelete = (id) => setHistory(deleteHistoryEntry(id));
  const handleHistoryClear = () => {
    clearHistory();
    setHistory([]);
  };
  const handleHistoryStatusChange = (id, status) => setHistory(updateHistoryEntry(id, { status }));

  const isBusy =
    loading || honestLoading || fullAppLoading || analysisLoading || savingBase || rendering;
  const showLocalAnalysis =
    atsMatch &&
    (lastAction === "check-ats" || lastAction === "improve") &&
    atsMatch.adaptation_mode === "local";
  const showAdaptedCv = Boolean(cvData);

  const actionCards = useMemo(
    () => [
      {
        id: "check-ats",
        title: t("actionsGrid.checkAtsTitle"),
        desc: t("actionsGrid.checkAtsDesc"),
        icon: ScanSearch,
        ai: false,
        eta: t("actionsGrid.etaCheck"),
        loading: analysisLoading && lastAction === "check-ats",
        label: analysisLoading && lastAction === "check-ats" ? t("actions.checkingAts") : t("actions.checkAts"),
        onClick: () => handleLocalAnalysis("check-ats"),
      },
      {
        id: "improve",
        title: t("actionsGrid.improveTitle"),
        desc: t("actionsGrid.improveDesc"),
        icon: Lightbulb,
        ai: false,
        eta: t("actionsGrid.etaCheck"),
        loading: analysisLoading && lastAction === "improve",
        label: analysisLoading && lastAction === "improve" ? t("actions.improving") : t("actions.improve"),
        onClick: () => handleLocalAnalysis("improve"),
      },
      {
        id: "honest",
        title: t("actionsGrid.honestTitle"),
        desc: t("actionsGrid.honestDesc"),
        icon: Target,
        ai: true,
        eta: t("actionsGrid.etaHonest"),
        loading: honestLoading,
        label: honestLoading ? t("honest.adapting") : t("honest.action"),
        onClick: () => handleAdapt("honest"),
      },
      {
        id: "adapt",
        title: t("actionsGrid.adaptTitle"),
        desc: t("actionsGrid.adaptDesc"),
        icon: Sparkles,
        ai: true,
        eta: t("actionsGrid.etaAdapt"),
        loading: loading,
        label: loading ? t("actions.adapting") : t("actions.adapt"),
        onClick: () => handleAdapt("ats-perfect"),
      },
      {
        id: "full",
        title: t("actionsGrid.fullTitle"),
        desc: t("actionsGrid.fullDesc"),
        icon: Rocket,
        ai: true,
        eta: t("actionsGrid.etaFull"),
        loading: fullAppLoading,
        label: fullAppLoading ? t("fullApp.loading") : t("actions.fullApp"),
        onClick: handleFullApplication,
      },
    ],
    [
      t,
      analysisLoading,
      lastAction,
      honestLoading,
      loading,
      fullAppLoading,
      handleLocalAnalysis,
      handleAdapt,
      handleFullApplication,
    ],
  );

  const inputClass = "input-field";

  return (
    <div className="mx-auto min-h-screen max-w-5xl px-4 py-8 pb-24 sm:px-6 md:pb-8">
      <motion.header
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 flex flex-wrap items-start justify-between gap-4"
      >
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-600">{t("app.badge")}</p>
          <h1 className="text-3xl font-extrabold tracking-tight text-neutral-900 sm:text-4xl">{t("app.title")}</h1>
          <p className="mt-2 max-w-xl text-neutral-700">{t("app.subtitle")}</p>
          <button type="button" onClick={handleLoadDemo} className="mt-3 text-sm font-medium text-neutral-700 underline hover:text-neutral-900">
            {t("demo.button")}
          </button>
        </div>
        <select
          aria-label={t("app.uiLanguage")}
          className="rounded-xl border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 shadow-sm"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
        >
          {uiLanguages.map((lang) => (
            <option key={lang.id} value={lang.id}>
              {lang.label}
            </option>
          ))}
        </select>
      </motion.header>

      <main className="space-y-6">
        {backendStatus !== "online" && (
          <div
            className={clsx(
              "rounded-xl border px-4 py-3 text-sm",
              backendStatus === "checking" && "border-neutral-200 bg-white text-neutral-600",
              backendStatus === "waking" && "border-amber-200 bg-amber-50 text-amber-900",
              backendStatus === "offline" && "border-rose-200 bg-rose-50 text-rose-800",
            )}
            role="status"
          >
            {backendStatus === "checking" && t("backend.checking")}
            {backendStatus === "waking" && t("backend.waking")}
            {backendStatus === "offline" &&
              (isSplitDeployMisconfigured() ? t("backend.offlineVercel") : t("backend.offline"))}
            {backendStatus === "offline" && (
              <p className="mt-2 text-xs opacity-80">
                {t("backend.offlineHint").replace("{url}", getApiBaseForDisplay() || "/health")}
              </p>
            )}
          </div>
        )}

        <FlowGuide currentStep={flowStep} />

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <Label htmlFor="job-url">{t("urlImport.label")}</Label>
            <div className="mb-4 flex gap-2">
              <input
                id="job-url"
                type="url"
                className={clsx(inputClass, "flex-1")}
                placeholder={t("urlImport.placeholder")}
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
              />
              <button
                type="button"
                onClick={handleImportUrl}
                disabled={urlImportLoading || !jobUrl.trim()}
                className="btn-secondary shrink-0 px-4"
              >
                {urlImportLoading ? t("urlImport.loading") : t("urlImport.button")}
              </button>
            </div>
            <Label htmlFor="job-description">{t("job.label")}</Label>
            <textarea
              id="job-description"
              className={clsx(inputClass, "min-h-[200px] resize-y")}
              placeholder={t("job.placeholder")}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={8}
            />
            {offerLanguage?.name && (
              <p className="mt-2 text-xs text-neutral-600" role="status">
                {t("job.offerLanguage").replace("{language}", offerLanguage.name)}
              </p>
            )}
          </Card>

          <Card>
            <Label htmlFor="cv-pdf">{t("cv.label")}</Label>
            {cvBase && (
              <div className="mb-4 flex items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                <div>
                  <p className="flex items-center gap-2 font-semibold text-neutral-900">
                    <FileText className="h-4 w-4" />
                    {t("cv.saved")}
                  </p>
                  <p className="text-sm text-neutral-600">
                    {cvBase.filename} · {formatDate(cvBase.savedAt, dateLocale)}
                  </p>
                  {cvBaseSummary(cvBase.cv) && (
                    <p className="mt-1 text-sm font-medium text-neutral-800">
                      {t("cv.parseSummary").replace("{summary}", cvBaseSummary(cvBase.cv))}
                    </p>
                  )}
                  {cvParseWarning && (
                    <p className="mt-2 text-xs text-amber-800" role="status">
                      {cvParseWarning}
                    </p>
                  )}
                </div>
                <button type="button" onClick={handleRemoveCvBase} className="text-sm text-neutral-600 hover:text-rose-700">
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
                "flex w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-8 text-neutral-700 transition",
                dragOver ? "border-neutral-500 bg-neutral-100" : "border-neutral-300 bg-neutral-50 hover:border-neutral-400 hover:bg-white",
                savingBase && "pointer-events-none opacity-60",
              )}
            >
              {savingBase ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="text-sm font-medium">{t("cv.parsing")}</span>
                </>
              ) : (
                <>
                  <Upload className="h-5 w-5 text-neutral-700" />
                  <span className="text-sm font-medium">{t("cv.upload")}</span>
                  <span className="text-xs text-neutral-500">{t("cv.autoSaved")}</span>
                </>
              )}
            </div>
          </Card>
        </div>

        <PreflightPanel
          data={preflight}
          loading={preflightLoading}
          offerLanguage={offerLanguage}
          onAdaptClick={() => handleAdapt("ats-perfect")}
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {actionCards.map((action) => {
            const Icon = action.icon;
            const recommended = action.id === recommendedId;
            return (
              <button
                key={action.id}
                type="button"
                onClick={action.onClick}
                disabled={isBusy || !jobDescription.trim() || !hasCvSource}
                className={clsx(
                  "action-card text-left disabled:opacity-50",
                  recommended && "ring-2 ring-neutral-900 ring-offset-2",
                )}
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-100 text-neutral-800">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {recommended && (
                      <span className="rounded-full bg-neutral-900 px-2 py-0.5 text-xs font-semibold text-white">
                        {t("actionsGrid.recommended")}
                      </span>
                    )}
                    <span className="text-xs text-neutral-500">{action.eta}</span>
                    <span
                      className={clsx(
                        "rounded-full px-2.5 py-1 text-xs font-semibold",
                        action.ai ? "bg-amber-100 text-amber-950" : "bg-neutral-100 text-neutral-700",
                      )}
                    >
                      {action.ai ? (
                        <span className="inline-flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          {t("actions.usesAi")}
                        </span>
                      ) : (
                        t("actions.noAi")
                      )}
                    </span>
                  </div>
                </div>
                <h3 className="text-lg font-bold text-neutral-900">{action.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-neutral-700">{action.desc}</p>
                <div className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-neutral-900">
                  {action.loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {action.label}
                    </>
                  ) : (
                    action.label
                  )}
                </div>
              </button>
            );
          })}
        </div>

        <details className="rounded-2xl border border-neutral-200 bg-white px-5 py-4 shadow-sm">
          <summary className="cursor-pointer text-sm font-semibold text-neutral-800">{t("actionsGrid.advanced")}</summary>
          <div className="mt-4 space-y-4">
            <div>
              <Label htmlFor="template-id">{t("templates.label")}</Label>
              <select
                id="template-id"
                className={inputClass}
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
              >
                {(templates.length ? templates : [{ id: DEFAULT_TEMPLATE_ID, name: "Modern Pro" }]).map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-neutral-600">{t("templates.hint")}</p>
            </div>
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-3">
              <input
                type="checkbox"
                checked={fastMode}
                onChange={(e) => setFastMode(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-400"
              />
              <span>
                <span className="block text-sm font-medium text-neutral-900">{t("fullApp.fastMode")}</span>
                <span className="block text-xs text-neutral-600">{t("fullApp.fastModeHint")}</span>
              </span>
            </label>
          </div>
        </details>

        {(loading || honestLoading || fullAppLoading) && (
          <ApplicationProgress active={loading || honestLoading || fullAppLoading} indeterminate />
        )}

        <Card>
          {error && (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700" role="alert">
              {error}
            </div>
          )}

          {applicationReady && cvData && offerResearch && coverLetter && (
            <ApplicationReadyBanner
              companyName={offerResearch.company_name}
              jobTitle={offerResearch.job_title || atsMatch?.target_role}
              onDownloadCv={handleDownloadPdf}
              onDownloadLetter={() => downloadLetterText(coverLetter)}
              onDownloadPack={handleDownloadPack}
              downloading={rendering}
            />
          )}

          {showLocalAnalysis && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6 space-y-4">
              {lastAction === "check-ats" && (
                <div
                  className={clsx(
                    "rounded-xl border p-4 text-sm font-medium",
                    atsMatch.passes_ats ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-950",
                  )}
                >
                  {atsMatch.passes_ats ? t("ats.passesAts") : t("ats.failsAts")}
                </div>
              )}
              <ATSMatchPanel atsMatch={atsMatch} emphasizeImprovements={lastAction === "improve"} />
            </motion.div>
          )}

          {showAdaptedCv && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <ChangesPanel originalCv={originalCv} adaptedCv={cvData} atsMatch={atsMatch} />
              <ComparisonPanel originalCv={originalCv} adaptedCv={cvData} boosted={boosted} />
              {offerResearch && <OfferResearchPanel research={offerResearch} loading={false} />}
              {!showLocalAnalysis && (
                <ATSMatchPanel
                  atsMatch={atsMatch}
                  onReboost={canReboost ? handleReboost : undefined}
                  reboosting={reboosting}
                />
              )}
              {coverLetter && <CoverLetterPanel coverLetter={coverLetter} onChange={setCoverLetter} loading={false} />}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 pt-4">
                <div>
                  <h3 className="text-lg font-bold text-neutral-900">{t("result.title")}</h3>
                  {cvDirty && <p className="mt-1 text-xs text-amber-800">{t("result.dirtyHint")}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={handleDownloadPack} disabled={rendering} className="btn-primary px-4 py-2">
                    <Package className="h-4 w-4" />
                    {rendering ? t("pack.downloading") : t("pack.downloadPack")}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowEditor((v) => !v)}
                    className={clsx("btn-secondary px-4 py-2", showEditor && "bg-neutral-100 ring-1 ring-neutral-300")}
                  >
                    {showEditor ? <Eye className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                    {showEditor ? t("actions.preview") : t("actions.edit")}
                  </button>
                  <button type="button" onClick={handleUpdatePdf} disabled={rendering} className="btn-secondary px-4 py-2">
                    <RefreshCw className={clsx("h-4 w-4", rendering && "animate-spin")} />
                    {rendering ? t("result.updating") : t("result.updatePdf")}
                  </button>
                  <button type="button" onClick={handleDownloadPdf} disabled={rendering} className="btn-secondary px-4 py-2">
                    <Download className="h-4 w-4" />
                    {t("actions.download")}
                  </button>
                  <button type="button" onClick={handleDownloadAtsPdf} disabled={rendering} className="btn-secondary px-4 py-2">
                    <FileText className="h-4 w-4" />
                    {t("actions.downloadAts")}
                  </button>
                  <button type="button" onClick={handleDownloadAtsTxt} disabled={rendering} className="btn-secondary px-4 py-2">
                    <Mail className="h-4 w-4" />
                    {t("actions.downloadAtsTxt")}
                  </button>
                </div>
              </div>

              {showEditor ? (
                <CVEditor cv={cvData} onChange={handleCvChange} />
              ) : (
                <>
                  <p className="text-xs text-neutral-600">{t("result.previewHint")}</p>
                  <CVPreview cv={cvData} />
                </>
              )}

              {pdfData?.base64 && (
                <div className="overflow-hidden rounded-2xl border border-neutral-200">
                  <p className="border-b border-neutral-200 bg-neutral-50 px-4 py-2 text-xs font-medium text-neutral-600">
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

          {!atsMatch && !cvData && !loading && !honestLoading && !fullAppLoading && !analysisLoading && (
            <p className="text-center text-sm text-neutral-600">{t("result.emptyHint")}</p>
          )}
        </Card>

        <HistoryPanel
          history={history}
          onSelect={handleHistorySelect}
          onDelete={handleHistoryDelete}
          onClear={handleHistoryClear}
          onStatusChange={handleHistoryStatusChange}
        />
      </main>

      <DownloadStickyBar
        visible={Boolean(cvData)}
        onDownloadPdf={handleDownloadPdf}
        onDownloadPack={handleDownloadPack}
        downloading={rendering}
        hasCoverLetter={Boolean(coverLetter)}
      />

      <footer className="mt-10 pb-8 text-center text-sm text-neutral-500">
        {t("footer.poweredBy")} {t("ai.gemini")}
      </footer>
    </div>
  );
}

export default App;
