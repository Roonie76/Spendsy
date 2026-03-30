import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Loader2,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
} from "lucide-react";
import { formatIndianCompact } from "../../../../../../packages/shared/utils/helpers";
import { apiFetch } from "../../api";
import { detectPdfType } from "../../utils/pdf/detectPdfType";
import OcrUnsupportedModal from "../upload/OcrUnsupportedModal";
import { parseDigitalPdfUpload } from "../../services/parser";

const StatementHub = ({ user, apiBaseUrl, showToast, refreshData }) => {
  const [history, setHistory] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [showUnsupportedPdfModal, setShowUnsupportedPdfModal] = useState(false);
  const [statementType, setStatementType] = useState("debit");

  const fileRef = useRef(null);

  useEffect(() => {
    fetchHistory();
  }, [user]);

  const fetchHistory = async () => {
    if (!user?.id) return;
    try {
      setLoadingHistory(true);
      const data = await apiFetch(`${apiBaseUrl}/statements/history`);
      setHistory(data?.data || data);
    } catch (e) {
      console.error("Failed to load statement history", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      showToast("Only PDF statements are supported in this upload flow.", "error");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }

    try {
      const pdfType = await detectPdfType(file);
      if (pdfType === "ocr") {
        console.warn("Frontend OCR detection triggered, but allowing upload to backend for robust verification.");
        showToast("Low text density detected. Attempting to parse anyway...", "info");
      }
    } catch (error) {
      console.error("PDF inspection error:", error);
      // Fallback to uploading if inspection fails
    }

    setUploading(true);
    try {
      showToast("Uploading and parsing PDF...", "info");
      const parseResponse = await parseDigitalPdfUpload(apiBaseUrl, file, statementType);



      const parsedPayload = parseResponse?.data || parseResponse;
      const txs = parsedPayload.transactions || [];

      if (txs.length === 0) {
        showToast("No transactions were found in this PDF. It might be an unsupported format.", "warning");
        return;
      }

      const savedCount = parsedPayload.saved_count !== undefined ? parsedPayload.saved_count : txs.length;
      const warnings = parsedPayload.meta?.warnings || [];

      if (warnings.length > 0) {
        showToast(warnings[0] || `Statement processed! Synced ${savedCount} transactions with warnings.`, "info");
      } else {
        showToast(`PDF processed! Synced ${savedCount} transactions.`, "success");
      }

      
      await Promise.all([
        fetchHistory(),
        refreshData?.(),
      ]);

    } catch (err) {
      console.error("Upload error:", err);
      
      if (
        err.code === "OCR_REQUIRED" || 
        err.body?.code === "OCR_REQUIRED" || 
        (err.message && err.message.includes("OCR_REQUIRED"))
      ) {
        setShowUnsupportedPdfModal(true);
      } else {
        showToast(err.message || "Error processing PDF. Please try again.", "error");
      }

      
      await apiFetch(`${apiBaseUrl}/statements/record`, {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          status: "failed",
          account_type: statementType === "debit" ? "Debit" : "Credit",
          tx_count: 0,

          reconciliation_score: 0
        }),
      }).catch(e => console.error("Could not log failed statement", e));
      
      await fetchHistory();
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "success": return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      case "pending": return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
      case "partial": return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      default: return <AlertTriangle className="w-5 h-5 text-rose-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "success": return "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
      case "pending": return "bg-blue-500/10 border-blue-500/20 text-blue-400";
      case "partial": return "bg-amber-500/10 border-amber-500/20 text-amber-400";
      default: return "bg-rose-500/10 border-rose-500/20 text-rose-400";
    }
  };

  return (
    <div className="space-y-6">
      {/* Account Type Toggle */}
      <div className="flex bg-slate-900/50 backdrop-blur-xl p-1 rounded-xl border border-white/5 max-w-[300px] mx-auto">
        <button
          onClick={() => setStatementType("debit")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            statementType === "debit"
              ? "bg-blue-500/20 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.1)]"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Debit Card
        </button>
        <button
          onClick={() => setStatementType("credit")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            statementType === "credit"
              ? "bg-purple-500/20 text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.1)]"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Credit Card
        </button>
      </div>

      <motion.div

        whileHover={{ scale: 1.01, borderColor: "rgba(59,130,246,0.5)" }}
        onClick={() => !uploading && fileRef.current.click()}
        className={`border-2 border-dashed border-white/10 rounded-[2.5rem] p-12 text-center cursor-pointer transition-all bg-white/[0.02] relative overflow-hidden backdrop-blur-xl ${
          uploading ? "opacity-80 cursor-not-allowed border-blue-500/30" : "hover:bg-white/5"
        }`}
      >
        {uploading ? (
            <div className="relative z-10 flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-400 mb-4 animate-spin" />
              <h3 className="font-bold text-white text-lg">Parsing PDF...</h3>
              <p className="text-[10px] text-slate-500 mt-2 uppercase tracking-widest">

                Extracting searchable text
              </p>
            </div>
          ) : (
          <div className="relative z-10">
            <div className="w-16 h-16 bg-blue-500/10 rounded-3xl flex items-center justify-center mx-auto mb-4 border border-blue-500/20 shadow-[0_0_30px_rgba(59,130,246,0.15)]">
              <UploadCloud className="w-8 h-8 text-blue-400" />
            </div>
            <h3 className="font-bold text-white text-xl">
              Upload {statementType === "debit" ? "Debit Card" : "Credit Card"} Statement
            </h3>


            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <span className="px-3 py-1 bg-white/5 rounded-full text-xs font-medium text-slate-300 border border-white/10">PDF</span>
              <button 
                type="button" 
                onClick={(e) => { e.stopPropagation(); setShowUnsupportedPdfModal(true); }} 
                className="px-3 py-1 bg-amber-500/10 hover:bg-amber-500/20 rounded-full text-xs font-medium text-amber-400 border border-amber-500/20 transition-colors flex items-center gap-1 cursor-pointer"
              >
                <AlertTriangle className="w-3 h-3" />
                Open OCR Convertor*
              </button>
            </div>
          </div>
        )}
        
        {!uploading && (
          <div 
            onClick={(e) => { e.stopPropagation(); setShowUnsupportedPdfModal(true); }}
            className="absolute bottom-5 left-6 flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors z-20 cursor-help text-[11px] font-medium"
          >
            <span>*OCR not supported</span>
            <HelpCircle className="w-3.5 h-3.5" />
          </div>
        )}
        <input
          type="file"
          ref={fileRef}
          onChange={handleFileUpload}
          className="hidden"
          accept=".pdf,application/pdf"
          disabled={uploading}
        />
      </motion.div>

      {/* Upload History */}
      <div className="bg-white/5 border border-white/10 rounded-[2rem] p-6 backdrop-blur-xl overflow-hidden relative">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 rounded-xl">
              <Clock className="w-5 h-5 text-indigo-400" />
            </div>
            <h3 className="font-bold text-white text-lg tracking-tight">Processing History</h3>
          </div>
        </div>

        {loadingHistory ? (
          <div className="py-12 flex justify-center">
            <Loader2 className="w-8 h-8 text-slate-600 animate-spin" />
          </div>
        ) : history.length === 0 ? (
          <div className="py-12 text-center text-slate-500 border border-dashed border-white/5 rounded-2xl">
            <FileText className="w-8 h-8 opacity-20 mx-auto mb-3" />
            <p className="text-sm">No statements uploaded yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((record, i) => (
              <motion.div
                key={record.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center justify-between p-4 bg-white/[0.03] border border-white/5 rounded-2xl hover:bg-white/5 transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-xl flex items-center justify-center ${getStatusColor(record.status)}`}>
                    {getStatusIcon(record.status)}
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-200 text-sm flex items-center gap-2">
                      {record.filename}
                    </h4>
                    <div className="flex items-center gap-3 mt-1 text-[11px] font-medium text-slate-500">
                      <span>{new Date(record.created_at).toLocaleDateString("en-IN", { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                      <span>•</span>
                      <span>{record.tx_count} transactions</span>
                      {record.account_type && (
                        <>
                          <span>•</span>
                          <span className={`uppercase tracking-tighter text-[9px] px-1.5 py-0.5 rounded ${
                            record.account_type.toLowerCase() === 'credit' 
                              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' 
                              : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                          }`}>
                            {record.account_type}
                          </span>
                        </>
                      )}
                    </div>

                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <div className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${getStatusColor(record.status)}`}>
                    {record.status}
                  </div>
                  {record.status === 'success' || record.status === 'partial' ? (
                     <span className="text-[10px] font-mono text-slate-400">Score: <span className="text-white">{(record.reconciliation_score * 100).toFixed(0)}%</span></span>
                  ) : null}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <OcrUnsupportedModal
        open={showUnsupportedPdfModal}
        onClose={() => setShowUnsupportedPdfModal(false)}
      />
    </div>
  );
};

export default StatementHub;
