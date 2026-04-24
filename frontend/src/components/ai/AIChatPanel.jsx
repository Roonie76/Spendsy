import React, { useEffect, useRef } from "react";
import { X, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

export default function AIChatPanel({
  isOpen,
  onClose,
  messages,
  input,
  setInput,
  onSend,
  isLoading,
  authMissing,
  model,
  setModel,
  onConfirmTool,
  onFeedback,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, isOpen]);

  return (
    <div className={`fixed inset-0 z-50 ${isOpen ? "" : "pointer-events-none"}`}>
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity ${isOpen ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
      />

      <div
        className={`absolute right-4 bottom-4 md:right-8 md:bottom-8 flex h-[80vh] w-[92vw] max-w-md flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0b1220]/95 shadow-2xl backdrop-blur-xl transition-all ${
          isOpen ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10">
              <Sparkles className="h-4 w-4 text-cyan-300" />
            </span>
            <div>
              <p className="text-sm font-semibold">
                TORA
              </p>
              <p className="text-[11px] text-slate-400">Private, personalized insights</p>
            </div>
          </div>

          {/* TORA+ toggle — disabled until fine-tuning is complete
          <div className="flex items-center gap-1.5 bg-white/5 rounded-2xl p-1 border border-white/10 ml-4 mr-auto">
            <button
              onClick={() => setModel("tora")}
              className={`px-3 py-1 rounded-xl text-[10px] font-bold transition-all ${
                model === "tora"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              TORA
            </button>
            <button
              onClick={() => setModel("tora_plus")}
              className={`px-3 py-1 rounded-xl text-[10px] font-bold transition-all flex items-center gap-1 ${
                model === "tora_plus"
                  ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              TORA+ <Sparkles className="h-2.5 w-2.5" />
            </button>
          </div>
          */}

          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-300 hover:bg-white/10"
            aria-label="Close Tora"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/10 p-4 text-xs text-slate-400">
              Ask anything about your spending, budgets, or savings. The copilot reads your latest
              financial context and responds instantly.
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((msg, idx) => (
              <motion.div
                key={`${msg.role}-${idx}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <MessageBubble
                  message={{
                    ...msg,
                    onConfirmTool: msg.toolCalls
                      ? (tool) => onConfirmTool?.(idx, tool)
                      : undefined,
                    onFeedback:
                      msg.role === "assistant" && onFeedback
                        ? (rating) => onFeedback(idx, rating)
                        : undefined,
                  }}
                />
              </motion.div>
            ))}
          </AnimatePresence>

          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <TypingIndicator />
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-white/10 px-4 py-3">
          {authMissing && (
            <div className="mb-2 text-xs text-rose-300">
              Sign in to your account to enable AI insights.
            </div>
          )}
          <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-3 py-2">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              placeholder="Ask about budgets, spending, taxes..."
              className="flex-1 resize-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
              disabled={isLoading || authMissing}
            />
            <button
              type="button"
              onClick={onSend}
              className="rounded-xl bg-cyan-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isLoading || authMissing || !input.trim()}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
