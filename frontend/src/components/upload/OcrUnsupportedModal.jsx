import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ExternalLink } from "lucide-react";

export const OCR_CONVERTER_URL = "https://www.ilovepdf.com/ocr-pdf";

const OcrUnsupportedModal = ({ open, onClose }) => {
  const handleOpenConverter = () => {
    window.open(OCR_CONVERTER_URL, "_blank", "noopener,noreferrer");
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            className="w-full max-w-md rounded-[2rem] border border-amber-500/20 bg-[#0f172a] p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="unsupported-pdf-title"
          >
            <div className="flex items-start gap-4">
              <div className="mt-1 flex h-11 w-11 items-center justify-center rounded-2xl border border-amber-500/20 bg-amber-500/10">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
              </div>
              <div className="flex-1">
                <h3 id="unsupported-pdf-title" className="text-lg font-bold text-white">
                  Scanned Document Detected
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  We currently only support digital (text-searchable) PDFs. Please use our recommended free online OCR converter to extract text into a new PDF, then upload the converted file here.
                </p>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-semibold text-slate-200 transition-colors hover:bg-white/10"
              >
                Close
              </button>
              <button
                type="button"
                onClick={handleOpenConverter}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              >
                Open Converter
                <ExternalLink className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
};

export default OcrUnsupportedModal;
