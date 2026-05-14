/**
 * ITRFilingPage.jsx
 * Wraps the ITR wizard with document upload cards that call the document-parser
 * microservice for OCR-based autofill.
 */
import React, { useState, useRef, useCallback } from "react";
import { Upload, CheckCircle, AlertTriangle, X, FileText, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { ITRForm, itrSampleSchema, generateITRFilename } from "../itr-form-feature";
import "../itr-form-feature/styles.css";

// ── Config ────────────────────────────────────────────────────────────────────
const DOC_PARSER_URL =
  import.meta.env.VITE_DOCUMENT_PARSER_URL || "http://localhost:8007";
const INTERNAL_KEY =
  import.meta.env.VITE_INTERNAL_API_KEY || "internal-dev-key-that-is-long-enough-32c";

// ── Deep-merge helper ─────────────────────────────────────────────────────────
function deepMerge(target, source) {
  const out = { ...target };
  for (const key of Object.keys(source || {})) {
    if (
      source[key] !== null &&
      source[key] !== undefined &&
      typeof source[key] === "object" &&
      !Array.isArray(source[key])
    ) {
      out[key] = deepMerge(target[key] || {}, source[key]);
    } else if (source[key] !== null && source[key] !== undefined) {
      out[key] = source[key];
    }
  }
  return out;
}

// ── Trust score badge ─────────────────────────────────────────────────────────
function TrustBadge({ score }) {
  const color =
    score >= 80 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
    : score >= 50 ? "text-yellow-400 bg-yellow-500/10 border-yellow-500/20"
    : "text-rose-400 bg-rose-500/10 border-rose-500/20";
  const label =
    score >= 80 ? "Verified" : score >= 50 ? "Warnings" : "Suspicious";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${color}`}>
      {score >= 80 ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
      {label} · {score}/100
    </span>
  );
}

// ── Individual upload card ─────────────────────────────────────────────────────
function UploadCard({ title, subtitle, endpoint, extraFields, onAutofill, userPan }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [showChecks, setShowChecks] = useState(false);
  const inputRef = useRef(null);

  const handleFile = useCallback(
    async (f) => {
      if (!f) return;
      setFile(f);
      setStatus("uploading");
      setErrorMsg("");
      setResult(null);

      const fd = new FormData();
      fd.append("file", f);
      if (userPan) fd.append("user_pan", userPan);
      if (extraFields) {
        Object.entries(extraFields).forEach(([k, v]) => {
          if (v !== undefined && v !== null) fd.append(k, v);
        });
      }

      try {
        const res = await fetch(`${DOC_PARSER_URL}${endpoint}`, {
          method: "POST",
          headers: { "x-internal-key": INTERNAL_KEY },
          body: fd,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Server error ${res.status}`);
        }
        const data = await res.json();
        setResult(data);
        setStatus("done");
        if (data.autofill) onAutofill(data.autofill);
      } catch (e) {
        setStatus("error");
        setErrorMsg(e.message || "Upload failed");
      }
    },
    [endpoint, extraFields, onAutofill, userPan],
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const reset = () => {
    setFile(null);
    setStatus("idle");
    setResult(null);
    setErrorMsg("");
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-semibold text-sm text-white">{title}</p>
          <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
        </div>
        {result?.verification?.trust_score !== undefined && (
          <TrustBadge score={result.verification.trust_score} />
        )}
      </div>

      {status === "idle" && (
        <div
          className="border-2 border-dashed border-white/10 rounded-xl p-6 text-center cursor-pointer hover:border-cyan-500/40 hover:bg-cyan-500/5 transition-all"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <Upload className="w-6 h-6 text-slate-500 mx-auto mb-2" />
          <p className="text-xs text-slate-400">Drop PDF here or <span className="text-cyan-400">browse</span></p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
        </div>
      )}

      {status === "uploading" && (
        <div className="flex items-center gap-3 py-4 px-3 rounded-xl bg-white/5">
          <Loader2 className="w-5 h-5 text-cyan-400 animate-spin shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-medium text-white truncate">{file?.name}</p>
            <p className="text-xs text-slate-400 mt-0.5">Running GLM OCR…</p>
          </div>
        </div>
      )}

      {status === "done" && result && (
        <div className="space-y-2">
          <div className="flex items-center gap-3 py-3 px-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{file?.name}</p>
              <p className="text-xs text-emerald-400 mt-0.5">
                {result.fields_extracted ?? "?"} fields extracted · {result.pages_processed ?? "?"} pages
              </p>
            </div>
            <button onClick={reset} className="text-slate-400 hover:text-white transition-colors shrink-0">
              <X className="w-4 h-4" />
            </button>
          </div>

          {result.verification?.checks?.length > 0 && (
            <div>
              <button
                onClick={() => setShowChecks((p) => !p)}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
              >
                {showChecks ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                Verification checks ({result.verification.checks.length})
              </button>
              {showChecks && (
                <div className="mt-2 space-y-1">
                  {result.verification.checks.map((c, i) => {
                    const color =
                      c.status === "passed" ? "text-emerald-400"
                      : c.status === "warning" ? "text-yellow-400"
                      : "text-rose-400";
                    return (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <span className={`${color} font-bold uppercase shrink-0 w-14`}>{c.status}</span>
                        <span className="text-slate-300">{c.message}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-3 py-3 px-3 rounded-xl bg-rose-500/5 border border-rose-500/10">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white">Upload failed</p>
            <p className="text-xs text-rose-400 mt-0.5 truncate">{errorMsg}</p>
          </div>
          <button onClick={reset} className="text-slate-400 hover:text-white transition-colors shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ITRFilingPage({ user, showToast, theme }) {
  const [autofillData, setAutofillData] = useState({});
  const [showUploader, setShowUploader] = useState(true);

  const mergeAutofill = useCallback((patch) => {
    setAutofillData((prev) => deepMerge(prev, patch));
    showToast?.("Fields auto-filled from document!", "success");
  }, [showToast]);

  const userPan = user?.pan || null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <FileText className="w-5 h-5 text-cyan-400" />
          <h2 className="text-2xl font-black text-white">ITR Filing</h2>
          <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            AY 2026-27
          </span>
        </div>
        <p className="text-sm text-slate-400">
          Upload your documents for auto-fill, then complete the filing wizard below.
        </p>
      </div>

      {/* Document Upload Section */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
        <button
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/5 transition-colors"
          onClick={() => setShowUploader((p) => !p)}
        >
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-semibold text-white">Document Upload &amp; Auto-fill</span>
            {Object.keys(autofillData).length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Data loaded
              </span>
            )}
          </div>
          {showUploader
            ? <ChevronUp className="w-4 h-4 text-slate-400" />
            : <ChevronDown className="w-4 h-4 text-slate-400" />
          }
        </button>

        {showUploader && (
          <div className="px-5 pb-5 grid sm:grid-cols-3 gap-4">
            <UploadCard
              title="Form 16"
              subtitle="TDS certificate from employer"
              endpoint="/parse/form16"
              userPan={userPan}
              onAutofill={mergeAutofill}
            />
            <UploadCard
              title="Broker Statement"
              subtitle="Capital gains from Zerodha / Groww"
              endpoint="/parse/broker"
              userPan={userPan}
              onAutofill={mergeAutofill}
            />
            <UploadCard
              title="Bank Statement"
              subtitle="Interest income certificate"
              endpoint="/parse/bank"
              userPan={userPan}
              onAutofill={mergeAutofill}
            />
          </div>
        )}
      </div>

      {/* ITR Form */}
      <ITRForm
        schema={itrSampleSchema}
        initialData={autofillData}
        storageKey="itr-live-draft"
        title="Tax Return Form"
        description="Fill in the details according to your records. Upload documents above for auto-fill."
        onSubmit={async (payload) => {
          try {
            const finalPayload = JSON.parse(JSON.stringify(payload));
            if (finalPayload.ITR?.ITR1?.CreationInfo) {
              delete finalPayload.ITR.ITR1.CreationInfo.Digest;
            }
            const canonicalString = JSON.stringify(finalPayload);
            const hashBuffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalString));
            const base64Digest = btoa(String.fromCharCode(...new Uint8Array(hashBuffer)));
            if (finalPayload.ITR?.ITR1?.CreationInfo) {
              finalPayload.ITR.ITR1.CreationInfo.Digest = base64Digest;
            }
            const blob = new Blob([JSON.stringify(finalPayload, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = generateITRFilename(finalPayload);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            showToast?.("ITR JSON downloaded!", "success");
          } catch (err) {
            console.error("ITR submission error:", err);
            showToast?.("Failed to generate ITR JSON", "error");
          }
        }}
      />
    </div>
  );
}
