import { Download, Package } from "lucide-react";
import clsx from "clsx";
import { useI18n } from "./i18n/I18nContext.jsx";

export default function DownloadStickyBar({
  visible,
  onDownloadPdf,
  onDownloadPack,
  downloading,
  hasCoverLetter,
}) {
  const { t } = useI18n();

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-neutral-200 bg-white/95 p-3 shadow-lg backdrop-blur md:hidden">
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
    </div>
  );
}
