import React from "react";
import { Sparkles } from "lucide-react";

export default function FloatingAIButton({ isOpen, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "fixed bottom-6 right-24 md:right-8 md:bottom-8 z-40 flex items-center gap-2 rounded-full px-5 py-4 text-sm font-semibold shadow-xl transition-all " +
        "bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:scale-105 hover:shadow-cyan-500/30 " +
        (isOpen ? "opacity-0 pointer-events-none" : "opacity-100")
      }
      aria-label="Open Tora"
    >
      <Sparkles className="h-4 w-4" />
      Ask Tora
    </button>
  );
}
