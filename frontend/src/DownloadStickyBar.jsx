import { Download, Package } from "lucide-react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function DownloadStickyBar({
  visible,
  onDownloadPdf,
  onDownloadPack,
  downloading,
  hasCoverLetter,
}) {
  const { t } = useI18n();

  return (
    <AnimatePresence>
      {visible && (
    <motion.div
      initial={{ transform: "translateY(100%)" }}
      animate={{ transform: "translateY(0%)" }}
      exit={{ transform: "translateY(100%)", transition: { duration: 0.2 } }}
      transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
      className="fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-neutral-50/90 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_-12px_oklch(0.4_0.03_60/0.25)] backdrop-blur-md md:hidden">
      <div className="mx-auto flex max-w-5xl gap-2">
        <button
          type="button"
          onClick={onDownloadPdf}
          disabled={downloading}
          className="btn-primary flex-1 justify-center py-2.5 text-sm"
        >
          <Download className="h-4 w-4" />
          {t("sticky.downloadPdf")}
        </button>
        <button
          type="button"
          onClick={onDownloadPack}
          disabled={downloading}
          className={clsx("btn-secondary flex-1 justify-center py-2.5 text-sm")}
        >
          <Package className="h-4 w-4" />
          {hasCoverLetter ? t("sticky.downloadPack") : t("sticky.downloadPackShort")}
        </button>
      </div>
    </motion.div>
      )}
    </AnimatePresence>
  );
}
